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
