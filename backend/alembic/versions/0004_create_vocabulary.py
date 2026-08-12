"""Create vocabulary tables.

Revision ID: 0004
Revises: 0003
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "words",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("lemma", sa.String(length=128), nullable=False),
        sa.Column("phonetic", sa.String(length=128), nullable=True),
        sa.Column("definitions", sa.JSON(), nullable=True),
        sa.Column("provider", sa.String(length=64), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_words_lemma"), "words", ["lemma"], unique=True)
    op.create_table(
        "user_words",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("word_id", sa.String(length=36), nullable=False),
        sa.Column("familiarity", sa.String(length=24), nullable=False),
        sa.Column("encounter_count", sa.Integer(), nullable=False),
        sa.Column("wrong_count", sa.Integer(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["word_id"], ["words.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("word_id"),
    )
    op.create_index(
        op.f("ix_user_words_familiarity"),
        "user_words",
        ["familiarity"],
        unique=False,
    )
    op.create_index(op.f("ix_user_words_word_id"), "user_words", ["word_id"], unique=True)
    op.create_table(
        "word_occurrences",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_word_id", sa.String(length=36), nullable=False),
        sa.Column("book_id", sa.String(length=36), nullable=True),
        sa.Column("surface_form", sa.String(length=128), nullable=False),
        sa.Column("char_start", sa.Integer(), nullable=False),
        sa.Column("char_end", sa.Integer(), nullable=False),
        sa.Column("context", sa.Text(), nullable=False),
        sa.Column("source_book_title", sa.String(length=255), nullable=False),
        sa.Column("source_chapter_title", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["book_id"], ["books.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_word_id"], ["user_words.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_word_occurrences_book_id"),
        "word_occurrences",
        ["book_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_word_occurrences_user_word_id"),
        "word_occurrences",
        ["user_word_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_word_occurrences_user_word_id"), table_name="word_occurrences")
    op.drop_index(op.f("ix_word_occurrences_book_id"), table_name="word_occurrences")
    op.drop_table("word_occurrences")
    op.drop_index(op.f("ix_user_words_word_id"), table_name="user_words")
    op.drop_index(op.f("ix_user_words_familiarity"), table_name="user_words")
    op.drop_table("user_words")
    op.drop_index(op.f("ix_words_lemma"), table_name="words")
    op.drop_table("words")
