"""Add question table

Revision ID: 6313845d38d0
Revises: 95e628ecde59
Create Date: 2026-07-12 21:39:41.009969

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = "6313845d38d0"
down_revision: str | None = "95e628ecde59"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "question",
        sa.Column("question_text", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("asked_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["asked_by"], ["user.id"]),
        sa.ForeignKeyConstraint(["document_id"], ["document.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_question_asked_by"), "question", ["asked_by"], unique=False)
    op.create_index(op.f("ix_question_document_id"), "question", ["document_id"], unique=False)
    # NOTE: autogenerate proposed dropping ix_chunk_embedding_hnsw here — that
    # index is created via raw SQL (op.execute) in the previous migration, not
    # declared in SQLAlchemy metadata, so autogenerate can't see it and treats
    # it as "removed". Deliberately not doing that; the index is untouched.


def downgrade() -> None:
    op.drop_index(op.f("ix_question_document_id"), table_name="question")
    op.drop_index(op.f("ix_question_asked_by"), table_name="question")
    op.drop_table("question")
