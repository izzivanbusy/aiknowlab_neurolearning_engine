"""
Vocabulary learning loop.

Routes:
  GET  /vocab/{learner_id}/next   → stage-aware next item
  POST /vocab/seen                → record ENCOUNTER (no evaluation needed)
  POST /vocab/check               → evaluate RECOGNIZE / RECALL / PRODUCE
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.base import get_db
from app.db.models import (
    Attempt,
    Evidence,
    EvidenceSkillMap,
    LearnerSkillState,
    LearningItem,
    Skill,
)
from app.engine import evaluator, inference, scheduler

router = APIRouter(prefix="/vocab", tags=["vocab"])

MODULE_ID = "german_vocab_a1"

# Stage ordering: encounter must precede recognize, etc.
STAGE_ORDER = ["vocab_encounter", "vocab_recognize", "vocab_recall", "vocab_produce"]
STAGE_SUFFIX = {
    "vocab_encounter": "-ENC",
    "vocab_recognize": "-REC",
    "vocab_recall": "-RAL",
    "vocab_produce": "-PRO",
}


# ── Schemas ──────────────────────────────────────────────────────────────────

class VocabNextResponse(BaseModel):
    item_id: uuid.UUID
    item_code: str
    skill_code: str
    word: str
    word_type: str
    translation_en: str
    stage: str           # vocab_encounter | vocab_recognize | vocab_recall | vocab_produce
    stage_index: int     # 0–3
    prompt_for_learner: str
    gapped_sentence: str | None = None
    full_sentence: str | None = None
    hint_example: str | None = None
    examples: list[str] | None = None
    words_seen: int      # how many words done so far
    words_total: int


class SeenRequest(BaseModel):
    learner_id: uuid.UUID
    item_id: uuid.UUID


class SeenResponse(BaseModel):
    ok: bool
    next_stage: str


class CheckRequest(BaseModel):
    learner_id: uuid.UUID
    item_id: uuid.UUID
    input_text: str
    duration_ms: int | None = None


class SkillStateOut(BaseModel):
    skill_code: str
    acquisition_probability: float
    evidence_count: int


class CheckResponse(BaseModel):
    attempt_id: uuid.UUID
    feedback: str
    performance_score: float
    correct: bool
    acquisition_probability: float
    stage: str
    word: str


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_done_item_codes(
    learner_id: uuid.UUID, skill_id: uuid.UUID, db: AsyncSession
) -> set[str]:
    """Return item_type labels the learner has already attempted for this skill."""
    result = await db.execute(
        select(LearningItem.item_type)
        .join(Attempt, Attempt.item_id == LearningItem.id)
        .where(
            Attempt.learner_id == learner_id,
            LearningItem.skill_id == skill_id,
        )
    )
    return {r[0] for r in result.all()}


async def _count_words_done(learner_id: uuid.UUID, db: AsyncSession) -> int:
    """Count how many A1 words the learner has at least encountered."""
    result = await db.execute(
        select(LearnerSkillState)
        .join(Skill, Skill.id == LearnerSkillState.skill_id)
        .where(
            LearnerSkillState.learner_id == learner_id,
            Skill.module_id == MODULE_ID,
        )
    )
    return len(result.scalars().all())


# ── GET /vocab/{learner_id}/next ──────────────────────────────────────────────

@router.get("/{learner_id}/next", response_model=VocabNextResponse)
async def get_next_vocab_item(
    learner_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> VocabNextResponse:
    """
    Stage-aware next item selector.

    Priority:
    1. Any word with an incomplete stage (in STAGE_ORDER) — continue current word
    2. A word due for review (FSRS next_review <= now) that isn't fully mastered
    3. A brand-new word (never seen)
    """
    now = datetime.now(tz=timezone.utc)

    # Count total A1 words
    total_result = await db.execute(
        select(Skill).where(Skill.module_id == MODULE_ID)
    )
    all_skills = total_result.scalars().all()
    words_total = len(all_skills)

    words_seen = await _count_words_done(learner_id, db)

    # ── Priority 1: words currently in-flight (encounter done but not produce) ─
    skill_state_result = await db.execute(
        select(LearnerSkillState, Skill)
        .join(Skill, Skill.id == LearnerSkillState.skill_id)
        .where(
            LearnerSkillState.learner_id == learner_id,
            Skill.module_id == MODULE_ID,
            LearnerSkillState.repetitions < 4,  # not yet through all stages
        )
        .order_by(LearnerSkillState.updated_at.asc())
    )
    in_flight = skill_state_result.all()

    for state, skill in in_flight:
        done_stages = await _get_done_item_codes(learner_id, skill.id, db)
        for stage_label in STAGE_ORDER:
            if stage_label not in done_stages:
                # This is the next stage for this word
                suffix = STAGE_SUFFIX[stage_label]
                item_result = await db.execute(
                    select(LearningItem).where(
                        LearningItem.skill_id == skill.id,
                        LearningItem.item_type == stage_label,
                    )
                )
                item = item_result.scalar_one_or_none()
                if item:
                    return _build_response(
                        item, skill, stage_label, words_seen, words_total
                    )

    # ── Priority 2: due for review ────────────────────────────────────────────
    due_result = await db.execute(
        select(LearnerSkillState, Skill)
        .join(Skill, Skill.id == LearnerSkillState.skill_id)
        .where(
            LearnerSkillState.learner_id == learner_id,
            Skill.module_id == MODULE_ID,
            LearnerSkillState.next_review <= now,
            LearnerSkillState.acquisition_probability < 0.95,
        )
        .order_by(LearnerSkillState.next_review.asc())
        .limit(1)
    )
    due_row = due_result.first()
    if due_row:
        state, skill = due_row
        # Review: use vocab_recognize or vocab_recall depending on acquisition_probability
        stage_label = (
            "vocab_recall" if state.acquisition_probability >= 0.6 else "vocab_recognize"
        )
        item_result = await db.execute(
            select(LearningItem).where(
                LearningItem.skill_id == skill.id,
                LearningItem.item_type == stage_label,
            )
        )
        item = item_result.scalar_one_or_none()
        if item:
            return _build_response(item, skill, stage_label, words_seen, words_total)

    # ── Priority 3: new word ──────────────────────────────────────────────────
    seen_skill_ids_result = await db.execute(
        select(LearnerSkillState.skill_id).where(
            LearnerSkillState.learner_id == learner_id
        )
    )
    seen_ids = {r[0] for r in seen_skill_ids_result.all()}

    new_skill_result = await db.execute(
        select(Skill)
        .where(
            Skill.module_id == MODULE_ID,
            Skill.id.not_in(seen_ids) if seen_ids else True,
        )
        .order_by(Skill.code.asc())
        .limit(1)
    )
    new_skill = new_skill_result.scalar_one_or_none()
    if not new_skill:
        raise HTTPException(status_code=404, detail="Alle Wörter gelernt! 🎉")

    item_result = await db.execute(
        select(LearningItem).where(
            LearningItem.skill_id == new_skill.id,
            LearningItem.item_type == "vocab_encounter",
        )
    )
    item = item_result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=500, detail="Encounter item missing for skill")

    return _build_response(item, new_skill, "vocab_encounter", words_seen, words_total)


def _build_response(
    item: LearningItem,
    skill: Skill,
    stage_label: str,
    words_seen: int,
    words_total: int,
) -> VocabNextResponse:
    c = item.content
    return VocabNextResponse(
        item_id=item.id,
        item_code=item.code,
        skill_code=skill.code,
        word=c.get("word", skill.name),
        word_type=c.get("word_type", ""),
        translation_en=c.get("translation_en", ""),
        stage=stage_label,
        stage_index=STAGE_ORDER.index(stage_label),
        prompt_for_learner=c.get("prompt_for_learner", ""),
        gapped_sentence=c.get("gapped_sentence"),
        full_sentence=c.get("full_sentence"),
        hint_example=c.get("hint_example"),
        examples=c.get("examples"),
        words_seen=words_seen,
        words_total=words_total,
    )


# ── POST /vocab/seen (ENCOUNTER — no evaluation) ──────────────────────────────

@router.post("/seen", response_model=SeenResponse, status_code=201)
async def mark_seen(
    body: SeenRequest,
    db: AsyncSession = Depends(get_db),
) -> SeenResponse:
    """
    Record that the learner has read the ENCOUNTER card.
    No AI evaluation — just persist the attempt and create/update skill state.
    """
    item_result = await db.execute(
        select(LearningItem)
        .where(LearningItem.id == body.item_id)
        .options(selectinload(LearningItem.skill))
    )
    item = item_result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    skill = item.skill
    content = item.content

    # Persist attempt
    attempt = Attempt(
        id=uuid.uuid4(),
        learner_id=body.learner_id,
        item_id=body.item_id,
        stage="encounter",
        input_text=None,
    )
    db.add(attempt)
    await db.flush()

    # Minimal evidence record
    evidence = Evidence(
        id=uuid.uuid4(),
        attempt_id=attempt.id,
        observation={"action": "encounter", "word": content.get("word")},
        signals={"performance_score": 0.5, "retrieval_success": False},
        skill_demonstration={
            "functional": False,
            "context_appropriate": False,
            "independent": False,
            "generalized": False,
        },
        metacognitive_flags={},
        raw_feedback_for_learner="",
    )
    db.add(evidence)
    await db.flush()

    # EvidenceSkillMap
    skill_code = skill.code
    esm_weights = content.get("evidence_skill_map", {}).get(
        skill_code, {"signal_weight": 0.2, "evidence_strength": 0.1}
    )
    esm = EvidenceSkillMap(
        id=uuid.uuid4(),
        evidence_id=evidence.id,
        skill_id=skill.id,
        signal_weight=esm_weights["signal_weight"],
        evidence_strength=esm_weights["evidence_strength"],
    )
    db.add(esm)

    # Create or update LearnerSkillState (minimal — just marks the word as started)
    state_result = await db.execute(
        select(LearnerSkillState).where(
            LearnerSkillState.learner_id == body.learner_id,
            LearnerSkillState.skill_id == skill.id,
        )
    )
    state = state_result.scalar_one_or_none()
    if not state:
        state = LearnerSkillState(
            id=uuid.uuid4(),
            learner_id=body.learner_id,
            skill_id=skill.id,
            acquisition_probability=0.1,
            confidence_in_estimate=0.0,
            evidence_count=1,
            stability=1.0,
            difficulty=skill.base_difficulty,
            repetitions=1,
            lapses=0,
        )
        db.add(state)
    else:
        state.evidence_count += 1
        state.repetitions += 1

    await db.commit()
    return SeenResponse(ok=True, next_stage="vocab_recognize")


# ── POST /vocab/check (RECOGNIZE / RECALL / PRODUCE) ─────────────────────────

@router.post("/check", response_model=CheckResponse, status_code=201)
async def check_attempt(
    body: CheckRequest,
    db: AsyncSession = Depends(get_db),
) -> CheckResponse:
    """
    Evaluate a learner's answer for RECOGNIZE, RECALL, or PRODUCE stages.
    Runs the full Bayesian + FSRS update pipeline.
    """
    item_result = await db.execute(
        select(LearningItem)
        .where(LearningItem.id == body.item_id)
        .options(selectinload(LearningItem.skill), selectinload(LearningItem.context))
    )
    item = item_result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    skill = item.skill
    context = item.context
    content = item.content
    stage = item.item_type  # vocab_recognize | vocab_recall | vocab_produce

    # Map item_type to evaluator stage name
    stage_name_map = {
        "vocab_recognize": "retrieve",
        "vocab_recall": "retrieve",
        "vocab_produce": "generate",
    }
    eval_stage = stage_name_map.get(stage, "retrieve")

    # Call AI evaluator
    eval_result = await evaluator.evaluate(
        learner_input=body.input_text,
        item_prompt=content["prompt_for_learner"],
        context_label=context.label,
        transfer_distance=context.transfer_distance,
        context_variable=content.get("word"),
        evaluator_notes=content.get("evaluator_notes", ""),
        expected_skill_demonstration={
            "functional": True,
            "context_appropriate": True,
            "independent": stage == "vocab_produce",
            "generalized": False,
        },
    )

    signals = eval_result["signals"]
    skill_demonstration = eval_result["skill_demonstration"]
    metacognitive_flags = eval_result["metacognitive_flags"]
    performance_score: float = signals.get("performance_score", 0.0)

    # Persist Attempt
    attempt = Attempt(
        id=uuid.uuid4(),
        learner_id=body.learner_id,
        item_id=body.item_id,
        stage=eval_stage,
        input_text=body.input_text,
        duration_ms=body.duration_ms,
    )
    db.add(attempt)
    await db.flush()

    # Persist Evidence
    evidence = Evidence(
        id=uuid.uuid4(),
        attempt_id=attempt.id,
        observation=eval_result["observation"],
        signals=signals,
        skill_demonstration=skill_demonstration,
        metacognitive_flags=metacognitive_flags,
        raw_feedback_for_learner=eval_result["raw_feedback_for_learner"],
    )
    db.add(evidence)
    await db.flush()

    # EvidenceSkillMap
    skill_code = skill.code
    esm_weights = content.get("evidence_skill_map", {}).get(
        skill_code, {"signal_weight": 0.7, "evidence_strength": 0.6}
    )
    esm = EvidenceSkillMap(
        id=uuid.uuid4(),
        evidence_id=evidence.id,
        skill_id=skill.id,
        signal_weight=esm_weights["signal_weight"],
        evidence_strength=esm_weights["evidence_strength"],
    )
    db.add(esm)

    # Load or create LearnerSkillState
    state_result = await db.execute(
        select(LearnerSkillState).where(
            LearnerSkillState.learner_id == body.learner_id,
            LearnerSkillState.skill_id == skill.id,
        )
    )
    state = state_result.scalar_one_or_none()
    if not state:
        state = LearnerSkillState(
            id=uuid.uuid4(),
            learner_id=body.learner_id,
            skill_id=skill.id,
            acquisition_probability=0.1,
            confidence_in_estimate=0.0,
            evidence_count=0,
            stability=1.0,
            difficulty=skill.base_difficulty,
            repetitions=0,
            lapses=0,
        )
        db.add(state)

    # Bayesian update
    effective_strength = esm_weights["signal_weight"] * esm_weights["evidence_strength"]
    new_p = inference.update_acquisition_probability(
        prior_p=state.acquisition_probability,
        skill_demonstration=skill_demonstration,
        signals=signals,
        evidence_strength=effective_strength,
    )
    new_evidence_count = state.evidence_count + 1
    new_confidence = inference.update_confidence(
        current_confidence=state.confidence_in_estimate,
        evidence_strength=effective_strength,
        evidence_count=new_evidence_count,
    )

    # FSRS scheduling
    rating = scheduler.performance_to_rating(
        performance_score=performance_score,
        retrieval_success=signals.get("retrieval_success", False),
    )
    new_stability, new_difficulty, new_reps, new_lapses, next_review = scheduler.fsrs_update(
        stability=state.stability,
        difficulty=state.difficulty,
        repetitions=state.repetitions,
        lapses=state.lapses,
        rating=rating,
    )

    # Apply updates
    state.acquisition_probability = new_p
    state.confidence_in_estimate = new_confidence
    state.evidence_count = new_evidence_count
    state.stability = new_stability
    state.difficulty = new_difficulty
    state.repetitions = new_reps
    state.lapses = new_lapses
    state.last_review = datetime.now(tz=timezone.utc)
    state.next_review = next_review

    await db.commit()

    return CheckResponse(
        attempt_id=attempt.id,
        feedback=eval_result["raw_feedback_for_learner"],
        performance_score=performance_score,
        correct=performance_score >= 0.65,
        acquisition_probability=new_p,
        stage=stage,
        word=content.get("word", skill.name),
    )
