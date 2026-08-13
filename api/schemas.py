"""Pydantic request/response schemas."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------

class CreateLearnerRequest(BaseModel):
    l1_language: str = Field(..., examples=["ru", "en", "tr"])
    proficiency: str = Field(..., examples=["A1", "A2", "B1", "B2"])


class LearnerResponse(BaseModel):
    id: uuid.UUID
    l1_language: str
    proficiency: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Learning loop
# ---------------------------------------------------------------------------

class NextItemResponse(BaseModel):
    item_id: uuid.UUID
    item_code: str
    skill_code: str
    skill_name: str
    context_label: str
    transfer_distance: int
    prompt_for_learner: str
    context_variable: str | None = None


class SubmitAttemptRequest(BaseModel):
    learner_id: uuid.UUID
    item_id: uuid.UUID
    stage: str = Field(..., examples=["retrieve", "generate", "transfer"])
    input_text: str
    duration_ms: int | None = None
    learner_confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Optional self-reported confidence [0,1] for metacognitive signal",
    )


class SkillStateUpdate(BaseModel):
    skill_code: str
    acquisition_probability: float
    confidence_in_estimate: float
    evidence_count: int
    next_review: datetime | None


class AttemptResponse(BaseModel):
    attempt_id: uuid.UUID
    evidence_id: uuid.UUID
    feedback: str
    signals: dict[str, Any]
    skill_demonstration: dict[str, Any]
    metacognitive_flags: dict[str, Any]
    skill_states_updated: list[SkillStateUpdate]


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

class SkillStateResponse(BaseModel):
    skill_code: str
    skill_name: str
    acquisition_probability: float
    confidence_in_estimate: float
    evidence_count: int
    metacognitive_gap_count: int
    metacognitive_error_count: int
    next_review: datetime | None
    stability: float

    model_config = {"from_attributes": True}


class LearnerStateResponse(BaseModel):
    learner_id: uuid.UUID
    skill_states: list[SkillStateResponse]
