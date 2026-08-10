"""
Learning loop — the core of the engine.

Routes:
  GET  /loop/{learner_id}/next    → select next due learning item
  POST /loop/attempt              → submit learner input, run full pipeline
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.schemas import (
    AttemptResponse,
    NextItemResponse,
    SkillStateUpdate,
    SubmitAttemptRequest,
)
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

router = APIRouter(prefix="/loop", tags=["loop"])


# ---------------------------------------------------------------------------
# GET /loop/{learner_id}/next
# ---------------------------------------------------------------------------

@router.get("/{learner_id}/next", response_model=NextItemResponse)
async def get_next_item(
    learner_id: uuid.UUID,
    module_id: str = "german_job_interview",
    db: AsyncSession = Depends(get_db),
) -> NextItemResponse:
    """
    Select the next learning item for this learner.

    Priority:
    1. Overdue items (next_review <= now), lowest stability first
    2. Items with no state yet (never seen) — lowest base_difficulty first
    3. Interference filter: avoid two items from the same skill family in one batch
    """
    now = datetime.now(tz=timezone.utc)

    # Items with existing state that are due
    due_result = await db.execute(
        select(LearnerSkillState, LearningItem, Skill)
        .join(LearningItem, LearningItem.skill_id == LearnerSkillState.skill_id)
        .join(Skill, Skill.id == LearnerSkillState.skill_id)
        .where(
            LearnerSkillState.learner_id == learner_id,
            LearnerSkillState.next_review <= now,
            Skill.module_id == module_id,
        )
        .order_by(LearnerSkillState.next_review.asc(), LearnerSkillState.stability.asc())
        .limit(1)
        .options(selectinload(LearningItem.context), selectinload(LearningItem.skill))
    )
    row = due_result.first()

    if row:
        _, item, skill = row
    else:
        # No due items — pick an unseen item
        seen_skill_ids_result = await db.execute(
            select(LearnerSkillState.skill_id).where(
                LearnerSkillState.learner_id == learner_id
            )
        )
        seen_skill_ids = {r[0] for r in seen_skill_ids_result.all()}

        unseen_result = await db.execute(
            select(LearningItem, Skill)
            .join(Skill, Skill.id == LearningItem.skill_id)
            .where(
                Skill.module_id == module_id,
                Skill.id.not_in(seen_skill_ids) if seen_skill_ids else True,
            )
            .order_by(Skill.base_difficulty.asc())
            .limit(1)
            .options(selectinload(LearningItem.context), selectinload(LearningItem.skill))
        )
        unseen_row = unseen_result.first()
        if not unseen_row:
            raise HTTPException(status_code=404, detail="No items available")
        item, skill = unseen_row

    content = item.content
    return NextItemResponse(
        item_id=item.id,
        item_code=item.code,
        skill_code=skill.code,
        skill_name=skill.name,
        context_label=item.context.label,
        transfer_distance=item.context.transfer_distance,
        prompt_for_learner=content["prompt_for_learner"],
        context_variable=content.get("context_variable"),
    )


# ---------------------------------------------------------------------------
# POST /loop/attempt
# ---------------------------------------------------------------------------

@router.post("/attempt", response_model=AttemptResponse, status_code=201)
async def submit_attempt(
    body: SubmitAttemptRequest,
    db: AsyncSession = Depends(get_db),
) -> AttemptResponse:
    """
    Full pipeline for one learner attempt:

    1. Load item + context
    2. Call AI evaluator → structured observation
    3. Persist Attempt + Evidence
    4. Update EvidenceSkillMap entries
    5. Update LearnerSkillState (Bayesian inference + FSRS)
    6. Return feedback + state updates
    """

    # --- 1. Load item ---
    item_result = await db.execute(
        select(LearningItem)
        .where(LearningItem.id == body.item_id)
        .options(
            selectinload(LearningItem.context),
            selectinload(LearningItem.skill),
        )
    )
    item = item_result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Learning item not found")

    content = item.content
    context = item.context

    # --- 2. AI Evaluation ---
    eval_result = await evaluator.evaluate(
        learner_input=body.input_text,
        item_prompt=content["prompt_for_learner"],
        context_label=context.label,
        transfer_distance=context.transfer_distance,
        context_variable=content.get("context_variable"),
        evaluator_notes=content.get("evaluator_notes"),
        expected_skill_demonstration=content.get("expected_skill_demonstration", {}),
    )

    signals = eval_result["signals"]
    skill_demonstration = eval_result["skill_demonstration"]
    metacognitive_flags = eval_result["metacognitive_flags"]

    # Merge learner_confidence into metacognitive signal if provided
    if body.learner_confidence is not None:
        perf = signals.get("performance_score", 0.0)
        conf = body.learner_confidence
        if perf >= 0.8 and conf < 0.4:
            metacognitive_flags["possible_gap"] = True
            metacognitive_flags["note"] = (metacognitive_flags.get("note") or "") + \
                " [self-reported low confidence despite high performance]"
        if perf < 0.5 and conf > 0.8:
            metacognitive_flags["possible_error"] = True
            metacognitive_flags["note"] = (metacognitive_flags.get("note") or "") + \
                " [self-reported high confidence despite low performance]"

    # --- 3. Persist Attempt ---
    attempt = Attempt(
        id=uuid.uuid4(),
        learner_id=body.learner_id,
        item_id=body.item_id,
        stage=body.stage,
        input_text=body.input_text,
        duration_ms=body.duration_ms,
    )
    db.add(attempt)
    await db.flush()  # get attempt.id

    # --- 4. Persist Evidence ---
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
    await db.flush()  # get evidence.id

    # --- 5. EvidenceSkillMap + LearnerSkillState updates ---
    skill_map_entries: list[dict] = content.get("evidence_skill_map", {})
    # Format: {"SK-08": {"signal_weight": 0.9, "evidence_strength": 1.0}, ...}

    skill_states_updated: list[SkillStateUpdate] = []

    for skill_code, weights in skill_map_entries.items():
        signal_weight: float = weights["signal_weight"]
        evidence_strength: float = weights["evidence_strength"]

        # Load skill
        skill_result = await db.execute(
            select(Skill).where(Skill.code == skill_code)
        )
        skill = skill_result.scalar_one_or_none()
        if not skill:
            continue

        # Persist EvidenceSkillMap entry
        map_entry = EvidenceSkillMap(
            id=uuid.uuid4(),
            evidence_id=evidence.id,
            skill_id=skill.id,
            signal_weight=signal_weight,
            evidence_strength=evidence_strength,
        )
        db.add(map_entry)

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

        # Bayesian acquisition update (weighted by evidence_strength × signal_weight)
        effective_strength = evidence_strength * signal_weight
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

        # FSRS scheduling update
        rating = scheduler.performance_to_rating(
            performance_score=signals.get("performance_score", 0.0),
            retrieval_success=signals.get("retrieval_success", False),
        )
        new_stability, new_difficulty, new_reps, new_lapses, next_review = scheduler.fsrs_update(
            stability=state.stability,
            difficulty=state.difficulty,
            repetitions=state.repetitions,
            lapses=state.lapses,
            rating=rating,
        )

        # Metacognitive counters
        if metacognitive_flags.get("possible_gap"):
            state.metacognitive_gap_count += 1
        if metacognitive_flags.get("possible_error"):
            state.metacognitive_error_count += 1

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

        skill_states_updated.append(
            SkillStateUpdate(
                skill_code=skill_code,
                acquisition_probability=new_p,
                confidence_in_estimate=new_confidence,
                evidence_count=new_evidence_count,
                next_review=next_review,
            )
        )

    await db.commit()

    return AttemptResponse(
        attempt_id=attempt.id,
        evidence_id=evidence.id,
        feedback=eval_result["raw_feedback_for_learner"],
        signals=signals,
        skill_demonstration=skill_demonstration,
        metacognitive_flags=metacognitive_flags,
        skill_states_updated=skill_states_updated,
    )
