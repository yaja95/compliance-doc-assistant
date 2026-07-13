import os
from collections.abc import Generator

from sqlmodel import Session, create_engine

DATABASE_URL = os.getenv(
    "COMPLIANCE_DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/compliance_doc_assistant",
)

engine = create_engine(DATABASE_URL)


def get_session() -> Generator[Session]:
    with Session(engine) as session:
        yield session
