"""
SQLAlchemy ORM models for NeuroLearning Engine.

Architecture:
    LEARNER
        └── ATTEMPT ──► EVIDENCE ──► EVIDENCE_SKILL_MAP ──► LEARNER_SKILL_STATE
                            └── context (transfer_distance)

Scheduling (FSRS) and acquisition inference live in LEARNER_SKILL_STATE.
They are separate fields — FSRS is a planning model, not a brain model.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


# ---------------------------------------------------------------------------
# Learner
# ---------------------------------------------------------------------------

class Learner(Base):
    __tablename__ = "learners"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    l1_language: Mapped[str] = mapped_column(String(10), nullable=False)
    # ISO 639-1: "ru", "en", "tr", "ar", ...
    proficiency: Mapped[str] = mapped_column(String(10), nullable=False)
    # "A1" | "A2" | "B1" | "B2"
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    attempts: Mapped[list["Attempt"]] = relationship(back_populates="learner")
    skill_states: Mapped[list["LearnerSkillState"]] = relationship(back_populates="learner")


# ---------------------------------------------------------------------------
# Context (transfer distance taxonomy)
# ---------------------------------------------------------------------------

class Context(Base):
    __tablename__ = "contexts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    label: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    # "controlled_exercise" | "scenario_guided" | "scenario_free" | "unexpected_transfer"
    transfer_distance: Mapped[int] = mapped_column(Integer, nullable=False)
    # 0 = controlled exercise
    # 1 = guided scenario
    # 2 = free scenario
    # 3 = unexpected transfer (new context entirely)
    description: Mapped[str | None] = mapped_column(Text)


# ---------------------------------------------------------------------------
# Skill  (latent construct — not a task)
# ---------------------------------------------------------------------------

class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    module_id: Mapped[str] = mapped_column(String(100), nullable=False)
    # e.g. "german_job_interview"
    family_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    # interference cluster — items in same family avoided in same session
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    # e.g. "SK-08"
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    base_difficulty: Mapped[float] = mapped_column(Float, default=0.5)
    # prior over items — not learner-specific


# ---------------------------------------------------------------------------
# LearningItem  (a specific exercise targeting one skill)
# ---------------------------------------------------------------------------

class LearningItem(Base):
    __tablename__ = "learning_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skills.id"), nullable=False
    )
    context_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contexts.id"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    # e.g. "LI-08-01"
    item_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # "retrieve" | "generate" | "transfer"
    content: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # {
    #   "prompt_for_learner": str,
    #   "context_variable": str | None,   e.g. "organizational_register=very_formal"
    #   "evaluator_notes": str,
    #   "expected_skill_demonstration": {functional, context_appropriate, independent, generalized}
    # }

    skill: Mapped["Skill"] = relationship()
    context: Mapped["Context"] = relationship()


# ---------------------------------------------------------------------------
# Attempt  (raw event — what happened)
# ---------------------------------------------------------------------------

class Attempt(Base):
    __tablename__ = "attempts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    learner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("learners.id"), nullable=False
    )
    item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("learning_items.id"), nullable=False
    )
    stage: Mapped[str] = mapped_column(String(30), nullable=False)
    # "encounter" | "retrieve" | "generate" | "transfer"
    input_text: Mapped[str | None] = mapped_column(Text)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    learner: Mapped["Learner"] = relationship(back_populates="attempts")
    item: Mapped["LearningItem"] = relationship()
    evidence: Mapped["Evidence | None"] = relationship(back_populates="attempt", uselist=False)


# ---------------------------------------------------------------------------
# Evidence  (what the attempt tells us — the inference layer)
# ---------------------------------------------------------------------------

class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    attempt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("attempts.id"), unique=True, nullable=False
    )

    # --- Evaluator output: structured observation ---
    observation: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # {
    #   "produced_text": str,
    #   "register": "formal|informal|mixed",
    #   "completeness": float,
    #   "language_switches": bool
    # }

    signals: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # {
    #   "performance_score": float,       ← in signals, not standalone
    #   "retrieval_success": bool,
    #   "lexical_errors": [str],
    #   "morphological_errors": [str],
    #   "syntactic_errors": [str],
    #   "pragmatic_errors": [str],
    #   "register_consistent": bool,
    #   "target_skill_demonstrated": bool,
    #   "transfer_appropriate": bool | null
    # }

    skill_demonstration: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # {
    #   "functional": bool,
    #   "context_appropriate": bool,
    #   "independent": bool,
    #   "generalized": bool
    # }

    metacognitive_flags: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # {
    #   "possible_gap": bool,   — high performance, low confidence
    #   "possible_error": bool, — low performance, high confidence
    #   "note": str | null
    # }

    raw_feedback_for_learner: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    attempt: Mapped["Attempt"] = relationship(back_populates="evidence")
    skill_map: Mapped[list["EvidenceSkillMap"]] = relationship(back_populates="evidence")


# ---------------------------------------------------------------------------
# EvidenceSkillMap  (many-to-many: evidence → skills, with two weights)
# ---------------------------------------------------------------------------

class EvidenceSkillMap(Base):
    __tablename__ = "evidence_skill_map"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    evidence_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evidence.id"), nullable=False
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skills.id"), nullable=False
    )
    signal_weight: Mapped[float] = mapped_column(Float, nullable=False)
    # How strongly does this item address this skill? [0, 1]
    evidence_strength: Mapped[float] = mapped_column(Float, nullable=False)
    # How informative is this evidence for acquisition inference? [0, 1]

    evidence: Mapped["Evidence"] = relationship(back_populates="skill_map")
    skill: Mapped["Skill"] = relationship()


# ---------------------------------------------------------------------------
# LearnerSkillState  (per-learner × per-skill — the inference + scheduling state)
# ---------------------------------------------------------------------------

class LearnerSkillState(Base):
    __tablename__ = "learner_skill_states"
    __table_args__ = (UniqueConstraint("learner_id", "skill_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    learner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("learners.id"), nullable=False
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skills.id"), nullable=False
    )

    # --- Acquisition inference (Bayesian) ---
    # P(skill sufficiently acquired | observed evidence)
    # This is a model estimate, not a measured property of the learner.
    acquisition_probability: Mapped[float] = mapped_column(Float, default=0.1)
    confidence_in_estimate: Mapped[float] = mapped_column(Float, default=0.0)
    # Low when evidence_count is small; grows asymptotically toward 1.0
    evidence_count: Mapped[int] = mapped_column(Integer, default=0)

    # --- Metacognitive flags (updated across attempts) ---
    metacognitive_gap_count: Mapped[int] = mapped_column(Integer, default=0)
    metacognitive_error_count: Mapped[int] = mapped_column(Integer, default=0)

    # --- FSRS scheduling (planning model — not a brain model) ---
    stability: Mapped[float] = mapped_column(Float, default=1.0)
    # Estimated days until significant forgetting
    difficulty: Mapped[float] = mapped_column(Float, default=0.5)
    # Interaction of item.base_difficulty × learner; updated per attempt
    repetitions: Mapped[int] = mapped_column(Integer, default=0)
    lapses: Mapped[int] = mapped_column(Integer, default=0)
    last_review: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_review: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    learner: Mapped["Learner"] = relationship(back_populates="skill_states")
    skill: Mapped["Skill"] = relationship()
