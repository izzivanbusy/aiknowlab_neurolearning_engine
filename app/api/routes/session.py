"""Session management — create and retrieve learners."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import CreateLearnerRequest, LearnerResponse
from app.db.base import get_db
from app.db.models import Learner

router = APIRouter(prefix="/session", tags=["session"])


@router.post("/start", response_model=LearnerResponse, status_code=201)
async def start_session(
    body: CreateLearnerRequest,
    db: AsyncSession = Depends(get_db),
) -> Learner:
    """Create a new anonymous learner and return their ID."""
    learner = Learner(
        id=uuid.uuid4(),
        l1_language=body.l1_language,
        proficiency=body.proficiency,
    )
    db.add(learner)
    await db.commit()
    await db.refresh(learner)
    return learner


@router.get("/{learner_id}", response_model=LearnerResponse)
async def get_session(
    learner_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Learner:
    result = await db.execute(select(Learner).where(Learner.id == learner_id))
    learner = result.scalar_one_or_none()
    if not learner:
        raise HTTPException(status_code=404, detail="Learner not found")
    return learner
