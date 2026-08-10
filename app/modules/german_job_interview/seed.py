"""
Seed script for the german_job_interview module.

Inserts:
  - 4 Context rows (controlled_exercise → unexpected_transfer)
  - 13 Skills (SK-01 through SK-13)
  - 5 Learning Items for SK-08 (Sich vorstellen) with full evidence_skill_map

Run:
    python -m app.modules.german_job_interview.seed
"""

import asyncio
import uuid

from sqlalchemy import select

from app.db.base import AsyncSessionLocal
from app.db.models import Context, LearningItem, Skill


# ---------------------------------------------------------------------------
# Contexts
# ---------------------------------------------------------------------------

CONTEXTS = [
    {
        "label": "controlled_exercise",
        "transfer_distance": 0,
        "description": "Gap-fill or structured task with full scaffolding. No communicative pressure.",
    },
    {
        "label": "scenario_guided",
        "transfer_distance": 1,
        "description": "Scenario with explicit hints. Learner knows what to include.",
    },
    {
        "label": "scenario_free",
        "transfer_distance": 2,
        "description": "Scenario without hints. Learner must initiate and structure independently.",
    },
    {
        "label": "unexpected_transfer",
        "transfer_distance": 3,
        "description": "New context outside the training domain. Tests whether skill has generalized.",
    },
]

# ---------------------------------------------------------------------------
# Skills — german_job_interview
# ---------------------------------------------------------------------------

# Interference families
FAM_REGISTER = uuid.UUID("11111111-0000-0000-0000-000000000001")
FAM_GRAMMAR = uuid.UUID("11111111-0000-0000-0000-000000000002")
FAM_LEXICAL = uuid.UUID("11111111-0000-0000-0000-000000000003")
FAM_COMMUNICATIVE = uuid.UUID("11111111-0000-0000-0000-000000000004")

SKILLS = [
    # --- Foundations ---
    {"code": "SK-01", "name": "Formelles Register (Sie-Form)",
     "description": "Consistent use of formal address (Sie), avoidance of du and informal lexis.",
     "base_difficulty": 0.3, "family_id": FAM_REGISTER},
    {"code": "SK-02", "name": "Bewerbungsphrasen",
     "description": "Fixed formulaic phrases used in job application contexts.",
     "base_difficulty": 0.35, "family_id": FAM_LEXICAL},
    {"code": "SK-03", "name": "Berufsfeld-Vokabular",
     "description": "Domain vocabulary relevant to professional contexts.",
     "base_difficulty": 0.4, "family_id": FAM_LEXICAL},
    # --- Grammar in context ---
    {"code": "SK-04", "name": "Perfekt mit haben/sein",
     "description": "Past tense formation for describing professional experience.",
     "base_difficulty": 0.5, "family_id": FAM_GRAMMAR},
    {"code": "SK-05", "name": "Modalverben im Präsens",
     "description": "können, möchten, würde gerne — expressing ability and desire.",
     "base_difficulty": 0.4, "family_id": FAM_GRAMMAR},
    {"code": "SK-06", "name": "Konjunktiv II",
     "description": "könnte, würde, wäre — polite, conditional register.",
     "base_difficulty": 0.65, "family_id": FAM_GRAMMAR},
    {"code": "SK-07", "name": "Kausale Konnektoren",
     "description": "weil, da, deshalb, daher — causal reasoning structures.",
     "base_difficulty": 0.45, "family_id": FAM_GRAMMAR},
    # --- Communicative skills ---
    {"code": "SK-08", "name": "Sich vorstellen",
     "description": "Formal self-introduction in professional contexts.",
     "base_difficulty": 0.4, "family_id": FAM_COMMUNICATIVE},
    {"code": "SK-09", "name": "Berufserfahrung beschreiben",
     "description": "Describing work history and responsibilities using Perfekt and connectors.",
     "base_difficulty": 0.55, "family_id": FAM_COMMUNICATIVE},
    {"code": "SK-10", "name": "Stärken formulieren",
     "description": "Articulating professional strengths with evidence and hedging.",
     "base_difficulty": 0.6, "family_id": FAM_COMMUNICATIVE},
    {"code": "SK-11", "name": "Schwächen benennen (mit Strategie)",
     "description": "Naming a weakness while reframing it strategically (Konjunktiv II).",
     "base_difficulty": 0.7, "family_id": FAM_COMMUNICATIVE},
    {"code": "SK-12", "name": "Motivation ausdrücken",
     "description": "Expressing motivation for applying using Konjunktiv II and connectors.",
     "base_difficulty": 0.6, "family_id": FAM_COMMUNICATIVE},
    {"code": "SK-13", "name": "Fragen an den Arbeitgeber stellen",
     "description": "Asking appropriate, register-correct questions to the interviewer.",
     "base_difficulty": 0.55, "family_id": FAM_COMMUNICATIVE},
]

# ---------------------------------------------------------------------------
# Learning Items — SK-08 only (MVP vertical slice)
# ---------------------------------------------------------------------------

ITEMS_SK08 = [
    {
        "code": "LI-08-01",
        "context_label": "controlled_exercise",
        "item_type": "retrieve",
        "content": {
            "prompt_for_learner": (
                "Sie bereiten sich auf ein Bewerbungsgespräch vor.\n"
                "Ergänzen Sie die Lücken mit passenden formellen Formulierungen:\n\n"
                "„Guten Tag, mein Name ___.\n"
                "Ich ___ [Berufsbezeichnung] und arbeite seit ___\n"
                "im Bereich ___.\n"
                "Ich habe mich auf diese Stelle beworben, weil ___.""
            ),
            "context_variable": None,
            "evaluator_notes": (
                "This is a controlled gap-fill. "
                "Check: Is Sie-Form consistent? Are Bewerbungsphrasen idiomatisch? "
                "If Perfekt appears, are auxiliary and Partizip correct? "
                "functional=false is expected (gap-fill is not real communication). "
                "independent=false is expected (scaffolding provided)."
            ),
            "expected_skill_demonstration": {
                "functional": False,
                "context_appropriate": True,
                "independent": False,
                "generalized": False,
            },
            "evidence_skill_map": {
                "SK-01": {"signal_weight": 0.8, "evidence_strength": 0.3},
                "SK-02": {"signal_weight": 0.9, "evidence_strength": 0.3},
                "SK-04": {"signal_weight": 0.4, "evidence_strength": 0.2},
                "SK-08": {"signal_weight": 0.5, "evidence_strength": 0.2},
            },
        },
    },
    {
        "code": "LI-08-02",
        "context_label": "scenario_guided",
        "item_type": "generate",
        "content": {
            "prompt_for_learner": (
                "Szenario: Sie sind bei einem ersten Gespräch bei Müller & Partner.\n"
                "Die HR-Managerin Frau Weber kommt auf Sie zu und sagt:\n"
                "„Guten Morgen. Stellen Sie sich bitte kurz vor."\n\n"
                "Hinweis: Erwähnen Sie Ihren Namen, Ihre aktuelle Position "
                "und warum Sie hier sind."
            ),
            "context_variable": None,
            "evaluator_notes": (
                "Guided scenario — hints were given. "
                "Note completeness: 0.5 = only scaffold followed, 1.0 = full independent introduction. "
                "functional=true expected (real communicative situation). "
                "independent=false (hint provided). "
                "transfer_appropriate=null (distance=1)."
            ),
            "expected_skill_demonstration": {
                "functional": True,
                "context_appropriate": True,
                "independent": False,
                "generalized": False,
            },
            "evidence_skill_map": {
                "SK-01": {"signal_weight": 0.7, "evidence_strength": 0.4},
                "SK-02": {"signal_weight": 0.6, "evidence_strength": 0.4},
                "SK-04": {"signal_weight": 0.6, "evidence_strength": 0.4},
                "SK-07": {"signal_weight": 0.4, "evidence_strength": 0.3},
                "SK-08": {"signal_weight": 0.8, "evidence_strength": 0.4},
            },
        },
    },
    {
        "code": "LI-08-03",
        "context_label": "scenario_guided",
        "item_type": "generate",
        "content": {
            "prompt_for_learner": (
                "Szenario: Ihre zweite Gesprächsrunde — diesmal mit dem Abteilungsleiter "
                "Dr. Hoffmann. Das Unternehmen ist bekannt für sehr formelle Kommunikation.\n"
                "Dr. Hoffmann schaut Sie an und wartet. Es gibt keine Frage.\n\n"
                "Stellen Sie sich vor."
            ),
            "context_variable": "organizational_register=very_formal",
            "evaluator_notes": (
                "No hint this time. Primary question: did the learner integrate the "
                "context variable (organizational_register=very_formal) into their language? "
                "Compare to LI-08-02: did they adapt, or produce the same output? "
                "context_appropriate=true only if register matches very_formal context. "
                "Pragmatic errors if Sie/du confusion or informal lexis appears. "
                "transfer_appropriate=null (distance=1)."
            ),
            "expected_skill_demonstration": {
                "functional": True,
                "context_appropriate": True,
                "independent": True,
                "generalized": False,
            },
            "evidence_skill_map": {
                "SK-01": {"signal_weight": 0.9, "evidence_strength": 0.5},
                "SK-02": {"signal_weight": 0.5, "evidence_strength": 0.4},
                "SK-05": {"signal_weight": 0.4, "evidence_strength": 0.4},
                "SK-08": {"signal_weight": 0.7, "evidence_strength": 0.5},
            },
        },
    },
    {
        "code": "LI-08-04",
        "context_label": "scenario_free",
        "item_type": "generate",
        "content": {
            "prompt_for_learner": (
                "Das Gespräch beginnt.\n"
                "Die Personalchefin schaut Sie erwartungsvoll an."
            ),
            "context_variable": None,
            "evaluator_notes": (
                "Free scenario — no hint, no prompt. "
                "The learner must take initiative. "
                "transfer_appropriate=true if: learner initiated without prompting, "
                "language is formally correct, introduction is contextually complete. "
                "transfer_appropriate=false if: learner waits, asks what to say, or register collapses. "
                "retrieval_failure if learner produces nothing — NOT metacognitive_error. "
                "This is the first item with a real transfer_appropriate signal (distance=2)."
            ),
            "expected_skill_demonstration": {
                "functional": True,
                "context_appropriate": True,
                "independent": True,
                "generalized": False,
            },
            "evidence_skill_map": {
                "SK-01": {"signal_weight": 0.7, "evidence_strength": 0.7},
                "SK-02": {"signal_weight": 0.6, "evidence_strength": 0.6},
                "SK-04": {"signal_weight": 0.6, "evidence_strength": 0.6},
                "SK-07": {"signal_weight": 0.5, "evidence_strength": 0.6},
                "SK-08": {"signal_weight": 1.0, "evidence_strength": 0.8},
            },
        },
    },
    {
        "code": "LI-08-05",
        "context_label": "unexpected_transfer",
        "item_type": "transfer",
        "content": {
            "prompt_for_learner": (
                "Sie sind auf einer Fachkonferenz für Digitalisierung.\n"
                "In der Kaffeepause stellt sich jemand neben Sie:\n"
                "„Hallo, ich bin Martin Brandt, CEO von Brandt Digital."\n"
                "Er schaut Sie an."
            ),
            "context_variable": "social_context=professional_networking",
            "evaluator_notes": (
                "IMPORTANT: This is NOT a test of whether the learner is better than in LI-08-04. "
                "It tests whether the skill has generalized beyond the job interview frame.\n\n"
                "transfer_appropriate=true if:\n"
                "- Learner adapts content to networking context (not interview)\n"
                "- Register is professional but NOT stiffly interview-formal\n"
                "- No copy-paste of interview-specific phrases\n\n"
                "transfer_appropriate=false if:\n"
                "- Learner uses interview phrases in wrong context "
                  "(e.g. 'Ich habe mich auf Ihre Stelle beworben')\n"
                "- Register collapses to informal under pressure\n\n"
                "KEY: transfer_success ≠ lexical similarity. "
                "A learner saying 'Hallo, ich bin Anna, ich arbeite im Bereich AI' "
                "demonstrates SK-08 even though it sounds different from the interview version. "
                "Evaluate functional demonstration, not surface form.\n\n"
                "generalized=true only if the skill was applied in the new social context correctly."
            ),
            "expected_skill_demonstration": {
                "functional": True,
                "context_appropriate": True,
                "independent": True,
                "generalized": True,
            },
            "evidence_skill_map": {
                "SK-01": {"signal_weight": 0.8, "evidence_strength": 0.9},
                "SK-05": {"signal_weight": 0.6, "evidence_strength": 0.9},
                "SK-08": {"signal_weight": 0.9, "evidence_strength": 1.0},
            },
        },
    },
]


# ---------------------------------------------------------------------------
# Seed runner
# ---------------------------------------------------------------------------

async def seed() -> None:
    async with AsyncSessionLocal() as db:
        # Contexts
        context_map: dict[str, Context] = {}
        for c in CONTEXTS:
            existing = (await db.execute(
                select(Context).where(Context.label == c["label"])
            )).scalar_one_or_none()
            if not existing:
                obj = Context(id=uuid.uuid4(), **c)
                db.add(obj)
                await db.flush()
                context_map[c["label"]] = obj
            else:
                context_map[c["label"]] = existing

        # Skills
        skill_map: dict[str, Skill] = {}
        for s in SKILLS:
            existing = (await db.execute(
                select(Skill).where(Skill.code == s["code"])
            )).scalar_one_or_none()
            if not existing:
                obj = Skill(
                    id=uuid.uuid4(),
                    module_id="german_job_interview",
                    **s,
                )
                db.add(obj)
                await db.flush()
                skill_map[s["code"]] = obj
            else:
                skill_map[s["code"]] = existing

        # Learning Items
        sk08 = skill_map["SK-08"]
        for item_data in ITEMS_SK08:
            existing = (await db.execute(
                select(LearningItem).where(LearningItem.code == item_data["code"])
            )).scalar_one_or_none()
            if not existing:
                ctx = context_map[item_data["context_label"]]
                obj = LearningItem(
                    id=uuid.uuid4(),
                    skill_id=sk08.id,
                    context_id=ctx.id,
                    code=item_data["code"],
                    item_type=item_data["item_type"],
                    content=item_data["content"],
                )
                db.add(obj)

        await db.commit()
        print("Seed complete: contexts, skills, and SK-08 items inserted.")


if __name__ == "__main__":
    asyncio.run(seed())
