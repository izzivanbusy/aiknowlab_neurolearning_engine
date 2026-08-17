"""
Seed script — German Vocabulary A1 (Goethe Institut Wortliste).

Creates:
  - 4 vocab contexts (encounter, recognize, recall, produce)
  - 1 Skill per word (module_id = "german_vocab_a1")
  - 4 LearningItems per word (one per stage)

Run:  python -m app.modules.german_vocab_a1.seed
"""

import asyncio
import re
import uuid

from sqlalchemy import select

from app.db.base import AsyncSessionLocal
from app.db.models import Context, LearningItem, Skill
from app.modules.german_vocab_a1.data import VOCAB_A1

MODULE_ID = "german_vocab_a1"

VOCAB_CONTEXTS = [
    {
        "label": "vocab_encounter",
        "transfer_distance": 0,
        "description": "First exposure: read word, translation, and example sentence.",
    },
    {
        "label": "vocab_recognize",
        "transfer_distance": 1,
        "description": "Gap fill: see word in context with the target word blanked out.",
    },
    {
        "label": "vocab_recall",
        "transfer_distance": 2,
        "description": "Recall: given L1 translation, produce the German word/phrase.",
    },
    {
        "label": "vocab_produce",
        "transfer_distance": 3,
        "description": "Produce: write an original German sentence using the target word.",
    },
]


def _make_gapped(sentence: str, word: str) -> str:
    """Replace first occurrence of word (case-insensitive) with ___."""
    # Try the exact word first, then capitalized, then lower
    pattern = re.compile(re.escape(word), re.IGNORECASE)
    gapped, count = pattern.subn("___", sentence, count=1)
    if count == 0:
        # Word might appear as a compound or with prefix — just return unchanged
        return sentence
    return gapped


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        # ── 1. Ensure vocab contexts exist ───────────────────────────────────
        context_map: dict[str, uuid.UUID] = {}
        for ctx_data in VOCAB_CONTEXTS:
            result = await db.execute(
                select(Context).where(Context.label == ctx_data["label"])
            )
            ctx = result.scalar_one_or_none()
            if not ctx:
                ctx = Context(
                    id=uuid.uuid4(),
                    label=ctx_data["label"],
                    transfer_distance=ctx_data["transfer_distance"],
                    description=ctx_data["description"],
                )
                db.add(ctx)
                await db.flush()
                print(f"  [+] Context: {ctx_data['label']}")
            context_map[ctx_data["label"]] = ctx.id

        # ── 2. Seed each word ─────────────────────────────────────────────────
        new_skills = 0
        new_items = 0

        for i, (word, article_alt, translation_en, word_type, goethe_ex) in enumerate(
            VOCAB_A1, start=1
        ):
            skill_code = f"VOC-A1-{i:03d}"

            # Check if skill already exists
            result = await db.execute(
                select(Skill).where(Skill.code == skill_code)
            )
            skill = result.scalar_one_or_none()

            if not skill:
                skill = Skill(
                    id=uuid.uuid4(),
                    module_id=MODULE_ID,
                    code=skill_code,
                    name=word,
                    description=f"{word_type} — {translation_en}",
                    base_difficulty=0.3,  # A1 words are relatively accessible
                )
                db.add(skill)
                await db.flush()
                new_skills += 1

            skill_id = skill.id
            skill_code_str = skill_code

            # Helper: check if item already exists
            async def item_exists(code: str) -> bool:
                r = await db.execute(
                    select(LearningItem.id).where(LearningItem.code == code)
                )
                return r.scalar_one_or_none() is not None

            # ── ENCOUNTER item ───────────────────────────────────────────────
            enc_code = f"{skill_code}-ENC"
            if not await item_exists(enc_code):
                display_word = word
                if article_alt:
                    display_word = f"{word} / {article_alt}"

                encounter_item = LearningItem(
                    id=uuid.uuid4(),
                    skill_id=skill_id,
                    context_id=context_map["vocab_encounter"],
                    code=enc_code,
                    item_type="vocab_encounter",
                    content={
                        "word": word,
                        "word_display": display_word,
                        "word_type": word_type,
                        "translation_en": translation_en,
                        "examples": [goethe_ex],
                        "prompt_for_learner": f"Neues Wort: {display_word}",
                        "evidence_skill_map": {
                            skill_code_str: {
                                "signal_weight": 0.2,
                                "evidence_strength": 0.1,
                            }
                        },
                    },
                )
                db.add(encounter_item)
                new_items += 1

            # ── RECOGNIZE item ───────────────────────────────────────────────
            rec_code = f"{skill_code}-REC"
            if not await item_exists(rec_code):
                gapped = _make_gapped(goethe_ex, word)
                recognize_item = LearningItem(
                    id=uuid.uuid4(),
                    skill_id=skill_id,
                    context_id=context_map["vocab_recognize"],
                    code=rec_code,
                    item_type="vocab_recognize",
                    content={
                        "word": word,
                        "word_type": word_type,
                        "translation_en": translation_en,
                        "gapped_sentence": gapped,
                        "full_sentence": goethe_ex,
                        "prompt_for_learner": f"Ergänze die Lücke:\n\n{gapped}",
                        "evaluator_notes": (
                            f"The missing word is '{word}' ({word_type}, meaning: {translation_en}). "
                            "Accept case-insensitive match. For verbs, also accept conjugated forms. "
                            "Give brief encouraging feedback."
                        ),
                        "evidence_skill_map": {
                            skill_code_str: {
                                "signal_weight": 0.7,
                                "evidence_strength": 0.6,
                            }
                        },
                    },
                )
                db.add(recognize_item)
                new_items += 1

            # ── RECALL item ──────────────────────────────────────────────────
            ral_code = f"{skill_code}-RAL"
            if not await item_exists(ral_code):
                prompt_recall = f"Wie sagt man auf Deutsch: '{translation_en}'?"
                recall_item = LearningItem(
                    id=uuid.uuid4(),
                    skill_id=skill_id,
                    context_id=context_map["vocab_recall"],
                    code=ral_code,
                    item_type="vocab_recall",
                    content={
                        "word": word,
                        "word_type": word_type,
                        "translation_en": translation_en,
                        "prompt_for_learner": prompt_recall,
                        "evaluator_notes": (
                            f"The target German word/expression is '{word}' ({word_type}). "
                            "Accept the word in isolation or in a short phrase. "
                            "For nouns, also accept with wrong article if the noun itself is correct. "
                            "Give brief, direct feedback."
                        ),
                        "evidence_skill_map": {
                            skill_code_str: {
                                "signal_weight": 0.85,
                                "evidence_strength": 0.8,
                            }
                        },
                    },
                )
                db.add(recall_item)
                new_items += 1

            # ── PRODUCE item ─────────────────────────────────────────────────
            pro_code = f"{skill_code}-PRO"
            if not await item_exists(pro_code):
                produce_item = LearningItem(
                    id=uuid.uuid4(),
                    skill_id=skill_id,
                    context_id=context_map["vocab_produce"],
                    code=pro_code,
                    item_type="vocab_produce",
                    content={
                        "word": word,
                        "word_type": word_type,
                        "translation_en": translation_en,
                        "prompt_for_learner": (
                            f"Schreibe einen eigenen Satz auf Deutsch mit dem Wort »{word}«."
                        ),
                        "hint_example": goethe_ex,
                        "evaluator_notes": (
                            f"The learner must use '{word}' ({word_type}, '{translation_en}') "
                            "correctly in an original German sentence. "
                            "Reward creativity and correct grammar. "
                            "Point out specific errors kindly. "
                            "Do NOT accept the Goethe example sentence verbatim."
                        ),
                        "evidence_skill_map": {
                            skill_code_str: {
                                "signal_weight": 1.0,
                                "evidence_strength": 1.0,
                            }
                        },
                    },
                )
                db.add(produce_item)
                new_items += 1

        await db.commit()
        print(
            f"\n✓ Vocab A1 seed complete: {new_skills} new skills, {new_items} new items "
            f"({len(VOCAB_A1)} words total)."
        )


if __name__ == "__main__":
    asyncio.run(seed())
