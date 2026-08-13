"""Add spaced review schedule fields.

Revision ID: 0006
Revises: 0005
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "user_words",
        sa.Column("review_stage", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "user_words",
        sa.Column("consecutive_correct", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "user_words",
        sa.Column("next_review_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "user_words",
        sa.Column("last_reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute("UPDATE user_words SET next_review_at = CURRENT_TIMESTAMP")
    with op.batch_alter_table("user_words") as batch_op:
        batch_op.alter_column("next_review_at", existing_type=sa.DateTime(), nullable=False)
    op.create_index(
        op.f("ix_user_words_next_review_at"),
        "user_words",
        ["next_review_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_user_words_next_review_at"), table_name="user_words")
    with op.batch_alter_table("user_words") as batch_op:
        batch_op.drop_column("last_reviewed_at")
        batch_op.drop_column("next_review_at")
        batch_op.drop_column("consecutive_correct")
        batch_op.drop_column("review_stage")
