import os
from collections.abc import Generator

import pytest
from sqlmodel import SQLModel

EXPECTED_TEST_DATABASE_URL = os.getenv(
    "COMPLIANCE_TEST_DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/compliance_doc_assistant_test",
)

# Tests deliberately override external DB config so destructive setup cannot hit real data.
os.environ["COMPLIANCE_DATABASE_URL"] = EXPECTED_TEST_DATABASE_URL

import compliance_doc_assistant.models  # noqa: F401, E402
from compliance_doc_assistant.database import engine  # noqa: E402
from compliance_doc_assistant.embeddings import EMBEDDING_DIMENSIONS  # noqa: E402

if "test" not in engine.url.database:
    raise RuntimeError(
        f"Test database must be a dedicated test database (name containing 'test'); "
        f"got {engine.url!s} instead."
    )


@pytest.fixture(autouse=True)
def reset_test_database() -> Generator[None]:
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    yield
    SQLModel.metadata.drop_all(engine)


def _fake_embed_texts(texts: list[str]) -> list[list[float]]:
    """Deterministic per-text fake vectors, distinct across different texts.

    Keeps the default suite fast — the real sentence-transformers model
    (loaded lazily on first real call) would otherwise download/load on every
    test run. pgvector_smoke_test/ is the one place that uses the real model.
    """
    vectors = []
    for text in texts:
        seed = sum(ord(c) for c in text) or 1
        vectors.append([((seed * (i + 1)) % 97) / 97 for i in range(EMBEDDING_DIMENSIONS)])
    return vectors


@pytest.fixture(autouse=True)
def _stub_embeddings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("compliance_doc_assistant.ingestion.embed_texts", _fake_embed_texts)
