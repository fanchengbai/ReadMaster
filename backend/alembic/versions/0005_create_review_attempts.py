"""Create review attempt records.

Revision ID: 0005
Revises: 0004
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "review_attempts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_word_id", sa.String(length=36), nullable=False),
        sa.Column("question_type", sa.String(length=32), nullable=False),
        sa.Column("prompt_snapshot", sa.Text(), nullable=False),
        sa.Column("correct_answer", sa.String(length=128), nullable=False),
        sa.Column("submitted_answer", sa.String(length=128), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_word_id"], ["user_words.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_review_attempts_user_word_id"),
        "review_attempts",
        ["user_word_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_review_attempts_is_correct"),
        "review_attempts",
        ["is_correct"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_review_attempts_is_correct"), table_name="review_attempts")
    op.drop_index(op.f("ix_review_attempts_user_word_id"), table_name="review_attempts")
    op.drop_table("review_attempts")
