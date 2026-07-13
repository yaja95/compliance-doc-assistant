"""Live-pgvector smoke test — NOT part of the default `uv run pytest` suite.

Deliberately kept outside tests/ so tests/conftest.py's stubbed-embeddings
autouse fixture never applies here — this is the one place that loads the
real sentence-transformers model and exercises real nearest-neighbor
queries against a live pgvector-enabled Postgres. Run explicitly:

    COMPLIANCE_DATABASE_URL=postgresql+psycopg://... uv run pytest pgvector_smoke_test/ -v

CI's pgvector-smoke job is the only place this normally runs, against a
real pgvector/pgvector:pg16 service container — see .github/workflows/ci.yml.
"""

import os

from sqlmodel import Session, select

EXPECTED_URL_PREFIX = "postgresql"

database_url = os.environ.get("COMPLIANCE_DATABASE_URL", "")
if not database_url.startswith(EXPECTED_URL_PREFIX):
    raise RuntimeError(
        "pgvector_smoke_test requires COMPLIANCE_DATABASE_URL to point at a "
        f"Postgres database (postgresql://... or postgresql+psycopg://...); got {database_url!r}."
    )

from compliance_doc_assistant.database import engine  # noqa: E402
from compliance_doc_assistant.embeddings import EMBEDDING_DIMENSIONS, embed_texts  # noqa: E402
from compliance_doc_assistant.models import Chunk, Document, User  # noqa: E402


def test_real_embeddings_have_expected_dimension() -> None:
    vectors = embed_texts(["Employees must report incidents within 24 hours."])

    assert len(vectors) == 1
    assert len(vectors[0]) == EMBEDDING_DIMENSIONS


def test_nearest_neighbor_query_ranks_semantically_similar_chunk_first() -> None:
    assert engine.dialect.name == "postgresql"

    with Session(engine) as session:
        user = User(username="pgvector-smoke-user", password_hash="unused")
        session.add(user)
        session.commit()
        session.refresh(user)

        document = Document(owner_id=user.id, filename="smoke.txt", source_format="txt")
        session.add(document)
        session.commit()
        session.refresh(document)

        contents = [
            "Employees must report safety incidents to compliance within 24 hours.",
            "The quarterly team picnic will be held in the parking lot on Friday.",
        ]
        vectors = embed_texts(contents)

        for i, (content, vector) in enumerate(zip(contents, vectors, strict=True)):
            session.add(
                Chunk(
                    document_id=document.id,
                    chunk_index=i,
                    content=content,
                    token_count=len(content.split()),
                    embedding=vector,
                )
            )
        session.commit()

        query_vector = embed_texts(["What is the incident reporting deadline?"])[0]

        nearest = session.exec(
            select(Chunk)
            .where(Chunk.document_id == document.id)
            .order_by(Chunk.embedding.cosine_distance(query_vector))
            .limit(1)
        ).first()

    assert nearest is not None
    assert "incident" in nearest.content.lower()
