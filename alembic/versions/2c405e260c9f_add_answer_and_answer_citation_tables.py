"""Add answer and answer citation tables

Revision ID: 2c405e260c9f
Revises: 6313845d38d0
Create Date: 2026-07-12 22:10:47.510923

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = "2c405e260c9f"
down_revision: str | None = "6313845d38d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "answer",
        sa.Column("answer_text", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("model_used", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["question_id"], ["question.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_answer_question_id"), "answer", ["question_id"], unique=False)
    op.create_table(
        "answercitation",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("answer_id", sa.Integer(), nullable=False),
        sa.Column("chunk_id", sa.Integer(), nullable=False),
        sa.Column("relevance_score", sa.Float(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["answer_id"], ["answer.id"]),
        sa.ForeignKeyConstraint(["chunk_id"], ["chunk.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_answercitation_answer_id"), "answercitation", ["answer_id"], unique=False
    )
    op.create_index(
        op.f("ix_answercitation_chunk_id"), "answercitation", ["chunk_id"], unique=False
    )
    # NOTE: autogenerate proposed dropping ix_chunk_embedding_hnsw here (same
    # false positive as the previous migration — it's raw-SQL, not tracked in
    # SQLAlchemy metadata). Deliberately not doing that; the index is untouched.


def downgrade() -> None:
    op.drop_index(op.f("ix_answercitation_chunk_id"), table_name="answercitation")
    op.drop_index(op.f("ix_answercitation_answer_id"), table_name="answercitation")
    op.drop_table("answercitation")
    op.drop_index(op.f("ix_answer_question_id"), table_name="answer")
    op.drop_table("answer")
