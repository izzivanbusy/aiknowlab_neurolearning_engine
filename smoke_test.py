"""
Smoke test — end-to-end loop run without a running server.

Walks through one full learning loop:
  1. Create learner
  2. Seed DB (contexts + skills + items)
  3. Get next item
  4. Submit attempt (calls real OpenAI API)
  5. Check skill state update

Run (with DB running and .env configured):
    python smoke_test.py
"""

import asyncio
import os
import sys

# Ensure project root on path
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import select

from app.db.base import AsyncSessionLocal, engine
from app.db.models import Base, LearnerSkillState
from app.db.models import Learner, LearningItem, Skill, Context
from app.modules.german_job_interview.seed import seed
from app.engine import evaluator, inference, scheduler

import uuid
from datetime import datetime, timezone


async def run() -> None:
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✓ Tables created")

    # Seed content
    await seed()
    print("✓ Seed complete")

    async with AsyncSessionLocal() as db:
        # Create learner
        learner = Learner(
            id=uuid.uuid4(),
            l1_language="ru",
            proficiency="B1",
        )
        db.add(learner)
        await db.commit()
        await db.refresh(learner)
        print(f"✓ Learner created: {learner.id}")

        # Get LI-08-01
        item_result = await db.execute(
            select(LearningItem)
            .where(LearningItem.code == "LI-08-01")
        )
        item = item_result.scalar_one()
        ctx_result = await db.execute(
            select(Context).where(Context.id == item.context_id)
        )
        ctx = ctx_result.scalar_one()
        print(f"✓ Item loaded: {item.code} (context={ctx.label}, distance={ctx.transfer_distance})")

        # Simulate learner input
        learner_input = (
            "Guten Tag, mein Name ist Anna Müller. "
            "Ich bin Softwareentwicklerin und arbeite seit drei Jahren "
            "im Bereich künstliche Intelligenz. "
            "Ich habe mich auf diese Stelle beworben, weil ich Ihre Arbeit "
            "an sprachverarbeitenden Systemen sehr spannend finde."
        )
        print(f"\n→ Learner input:\n  {learner_input}\n")

        # Call evaluator
        content = item.content
        eval_result = await evaluator.evaluate(
            learner_input=learner_input,
            item_prompt=content["prompt_for_learner"],
            context_label=ctx.label,
            transfer_distance=ctx.transfer_distance,
            context_variable=content.get("context_variable"),
            evaluator_notes=content.get("evaluator_notes"),
            expected_skill_demonstration=content.get("expected_skill_demonstration", {}),
        )
        print("✓ Evaluator returned:")
        print(f"  performance_score : {eval_result['signals']['performance_score']}")
        print(f"  retrieval_success : {eval_result['signals']['retrieval_success']}")
        print(f"  register_consistent: {eval_result['signals']['register_consistent']}")
        print(f"  functional        : {eval_result['skill_demonstration']['functional']}")
        print(f"  independent       : {eval_result['skill_demonstration']['independent']}")
        print(f"  feedback          : {eval_result['raw_feedback_for_learner'][:80]}...")

        # Run inference for SK-08
        skill_map = content["evidence_skill_map"]
        sw = skill_map["SK-08"]["signal_weight"]
        es = skill_map["SK-08"]["evidence_strength"]
        effective_strength = sw * es

        prior_p = 0.1
        new_p = inference.update_acquisition_probability(
            prior_p=prior_p,
            skill_demonstration=eval_result["skill_demonstration"],
            signals=eval_result["signals"],
            evidence_strength=effective_strength,
        )
        new_conf = inference.update_confidence(0.0, effective_strength, 1)
        print(f"\n✓ SK-08 state update:")
        print(f"  acquisition_probability: {prior_p:.3f} → {new_p:.3f}")
        print(f"  confidence_in_estimate : {new_conf:.3f}")
        print(f"  acquired               : {inference.is_acquired(new_p, new_conf)}")

        # FSRS
        rating = scheduler.performance_to_rating(
            performance_score=eval_result["signals"]["performance_score"],
            retrieval_success=eval_result["signals"]["retrieval_success"],
        )
        stab, diff, reps, lapses, next_review = scheduler.fsrs_update(1.0, 0.5, 0, 0, rating)
        print(f"\n✓ FSRS update:")
        print(f"  rating     : {rating}")
        print(f"  stability  : 1.0 → {stab:.2f} days")
        print(f"  next_review: {next_review.strftime('%Y-%m-%d %H:%M UTC')}")

    print("\n✓ Smoke test passed.")


if __name__ == "__main__":
    asyncio.run(run())
