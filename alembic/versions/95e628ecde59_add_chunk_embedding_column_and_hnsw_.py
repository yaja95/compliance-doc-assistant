"""Add chunk embedding column and hnsw index

Revision ID: 95e628ecde59
Revises: 31f0f34ecbbb
Create Date: 2026-07-12 21:10:11.344779

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "95e628ecde59"
down_revision: str | None = "31f0f34ecbbb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EMBEDDING_DIMENSIONS = 384


def upgrade() -> None:
    op.add_column("chunk", sa.Column("embedding", Vector(EMBEDDING_DIMENSIONS), nullable=True))
    op.execute(
        "CREATE INDEX ix_chunk_embedding_hnsw ON chunk USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_chunk_embedding_hnsw")
    op.drop_column("chunk", "embedding")
