"""Add answer review fields and review flag table

Revision ID: 2514bcabb082
Revises: 2c405e260c9f
Create Date: 2026-07-12 23:02:58.310117

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = "2514bcabb082"
down_revision: str | None = "2c405e260c9f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "reviewflag",
        sa.Column("reason", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("answer_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("reviewed_by", sa.Integer(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["answer_id"], ["answer.id"]),
        sa.ForeignKeyConstraint(["reviewed_by"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("answer_id"),
    )
    op.create_index(op.f("ix_reviewflag_answer_id"), "reviewflag", ["answer_id"], unique=False)
    # server_default so this doesn't fail against any existing Answer rows;
    # the Python-side default=False on the model covers new inserts.
    op.add_column(
        "answer",
        sa.Column("needs_review", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "answer", sa.Column("confidence_reason", sqlmodel.sql.sqltypes.AutoString(), nullable=True)
    )
    # NOTE: autogenerate proposed dropping ix_chunk_embedding_hnsw here (same
    # false positive as prior migrations). Deliberately not doing that.


def downgrade() -> None:
    op.drop_column("answer", "confidence_reason")
    op.drop_column("answer", "needs_review")
    op.drop_index(op.f("ix_reviewflag_answer_id"), table_name="reviewflag")
    op.drop_table("reviewflag")
