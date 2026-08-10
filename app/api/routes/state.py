"""Learner skill state — query acquisition and scheduling state."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.schemas import LearnerStateResponse, SkillStateResponse
from app.db.base import get_db
from app.db.models import Learner, LearnerSkillState

router = APIRouter(prefix="/state", tags=["state"])


@router.get("/{learner_id}", response_model=LearnerStateResponse)
async def get_learner_state(
    learner_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> LearnerStateResponse:
    """Return all skill states for a learner, with acquisition and scheduling info."""

    learner_result = await db.execute(
        select(Learner).where(Learner.id == learner_id)
    )
    if not learner_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Learner not found")

    states_result = await db.execute(
        select(LearnerSkillState)
        .where(LearnerSkillState.learner_id == learner_id)
        .options(selectinload(LearnerSkillState.skill))
        .order_by(LearnerSkillState.next_review.asc().nullsfirst())
    )
    states = states_result.scalars().all()

    skill_states = [
        SkillStateResponse(
            skill_code=s.skill.code,
            skill_name=s.skill.name,
            acquisition_probability=s.acquisition_probability,
            confidence_in_estimate=s.confidence_in_estimate,
            evidence_count=s.evidence_count,
            metacognitive_gap_count=s.metacognitive_gap_count,
            metacognitive_error_count=s.metacognitive_error_count,
            next_review=s.next_review,
            stability=s.stability,
        )
        for s in states
    ]

    return LearnerStateResponse(learner_id=learner_id, skill_states=skill_states)
