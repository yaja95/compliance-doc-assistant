import os
from collections.abc import Generator

from sqlmodel import Session, create_engine


def _with_psycopg_driver(url: str) -> str:
    """Managed Postgres hosts (Render, Heroku, Railway, ...) commonly hand out
    a bare `postgres://` or `postgresql://` connection string with no driver
    specified. SQLAlchemy needs the driver named explicitly to use psycopg3
    rather than defaulting to psycopg2 (not installed here).
    """
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


DATABASE_URL = _with_psycopg_driver(
    os.getenv(
        "COMPLIANCE_DATABASE_URL",
        "postgresql+psycopg://postgres:postgres@localhost:5432/compliance_doc_assistant",
    )
)

engine = create_engine(DATABASE_URL)


def get_session() -> Generator[Session]:
    with Session(engine) as session:
        yield session
