"""Initial schema

Revision ID: 0001
Revises:
Create Date: 2026-08-11
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # contexts
    op.create_table(
        "contexts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("label", sa.String(50), unique=True, nullable=False),
        sa.Column("transfer_distance", sa.Integer, nullable=False),
        sa.Column("description", sa.Text),
    )

    # learners
    op.create_table(
        "learners",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("l1_language", sa.String(10), nullable=False),
        sa.Column("proficiency", sa.String(10), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )

    # skills
    op.create_table(
        "skills",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("module_id", sa.String(100), nullable=False),
        sa.Column("family_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("code", sa.String(20), unique=True, nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("base_difficulty", sa.Float, default=0.5),
    )

    # learning_items
    op.create_table(
        "learning_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "skill_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("skills.id"),
            nullable=False,
        ),
        sa.Column(
            "context_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("contexts.id"),
            nullable=False,
        ),
        sa.Column("code", sa.String(20), unique=True, nullable=False),
        sa.Column("item_type", sa.String(50), nullable=False),
        sa.Column("content", postgresql.JSONB, nullable=False),
    )

    # attempts
    op.create_table(
        "attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "learner_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("learners.id"),
            nullable=False,
        ),
        sa.Column(
            "item_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("learning_items.id"),
            nullable=False,
        ),
        sa.Column("stage", sa.String(30), nullable=False),
        sa.Column("input_text", sa.Text),
        sa.Column("duration_ms", sa.Integer),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )

    # evidence
    op.create_table(
        "evidence",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "attempt_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("attempts.id"),
            unique=True,
            nullable=False,
        ),
        sa.Column("observation", postgresql.JSONB, nullable=False),
        sa.Column("signals", postgresql.JSONB, nullable=False),
        sa.Column("skill_demonstration", postgresql.JSONB, nullable=False),
        sa.Column("metacognitive_flags", postgresql.JSONB, nullable=False),
        sa.Column("raw_feedback_for_learner", sa.Text, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )

    # evidence_skill_map
    op.create_table(
        "evidence_skill_map",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "evidence_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("evidence.id"),
            nullable=False,
        ),
        sa.Column(
            "skill_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("skills.id"),
            nullable=False,
        ),
        sa.Column("signal_weight", sa.Float, nullable=False),
        sa.Column("evidence_strength", sa.Float, nullable=False),
    )

    # learner_skill_states
    op.create_table(
        "learner_skill_states",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "learner_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("learners.id"),
            nullable=False,
        ),
        sa.Column(
            "skill_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("skills.id"),
            nullable=False,
        ),
        sa.Column("acquisition_probability", sa.Float, default=0.1),
        sa.Column("confidence_in_estimate", sa.Float, default=0.0),
        sa.Column("evidence_count", sa.Integer, default=0),
        sa.Column("metacognitive_gap_count", sa.Integer, default=0),
        sa.Column("metacognitive_error_count", sa.Integer, default=0),
        sa.Column("stability", sa.Float, default=1.0),
        sa.Column("difficulty", sa.Float, default=0.5),
        sa.Column("repetitions", sa.Integer, default=0),
        sa.Column("lapses", sa.Integer, default=0),
        sa.Column("last_review", sa.DateTime(timezone=True)),
        sa.Column("next_review", sa.DateTime(timezone=True)),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("learner_id", "skill_id"),
    )


def downgrade() -> None:
    op.drop_table("learner_skill_states")
    op.drop_table("evidence_skill_map")
    op.drop_table("evidence")
    op.drop_table("attempts")
    op.drop_table("learning_items")
    op.drop_table("skills")
    op.drop_table("learners")
    op.drop_table("contexts")
