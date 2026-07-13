from datetime import UTC, datetime
from enum import StrEnum

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from pydantic import ConfigDict
from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel

from compliance_doc_assistant.embeddings import EMBEDDING_DIMENSIONS


def utc_now() -> datetime:
    return datetime.now(UTC)


class UserBase(SQLModel):
    username: str = Field(min_length=1, max_length=80)


class User(UserBase, table=True):
    __table_args__ = (UniqueConstraint("username"),)

    id: int | None = Field(default=None, primary_key=True)
    password_hash: str
    created_at: datetime = Field(default_factory=utc_now)


class UserCreate(UserBase):
    model_config = ConfigDict(extra="forbid")

    password: str = Field(min_length=8)


class UserRead(UserBase):
    id: int
    created_at: datetime


class AuthSession(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("token"),)

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    token: str = Field(index=True)
    created_at: datetime = Field(default_factory=utc_now)
    expires_at: datetime


class DocumentStatus(StrEnum):
    PENDING = "pending"
    CHUNKED = "chunked"
    EMBEDDED = "embedded"
    FAILED = "failed"


class DocumentBase(SQLModel):
    filename: str = Field(min_length=1, max_length=255)
    source_format: str = Field(max_length=10)


class Document(DocumentBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key="user.id", index=True)
    # Forced to a plain VARCHAR (not a native Postgres ENUM) so adding future
    # status values needs no migration — same rationale as User.role in
    # evalops-dashboard.
    status: DocumentStatus = Field(default=DocumentStatus.PENDING, sa_type=sa.String(length=20))
    uploaded_at: datetime = Field(default_factory=utc_now)


class DocumentRead(DocumentBase):
    id: int
    status: DocumentStatus
    uploaded_at: datetime


class ChunkBase(SQLModel):
    chunk_index: int
    section_label: str | None = Field(default=None, max_length=120)
    content: str
    token_count: int = Field(ge=0)


class Chunk(ChunkBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    document_id: int = Field(foreign_key="document.id", index=True)
    created_at: datetime = Field(default_factory=utc_now)
    # Never client-submittable — not on ChunkBase/ChunkRead, same
    # server-controlled-results placement as Document.status.
    embedding: list[float] | None = Field(default=None, sa_type=Vector(EMBEDDING_DIMENSIONS))


class ChunkRead(ChunkBase):
    id: int


class DocumentDetailRead(DocumentRead):
    chunks: list[ChunkRead]


class QuestionBase(SQLModel):
    question_text: str = Field(min_length=1)


class Question(QuestionBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    document_id: int = Field(foreign_key="document.id", index=True)
    asked_by: int = Field(foreign_key="user.id", index=True)
    created_at: datetime = Field(default_factory=utc_now)


class QuestionCreate(SQLModel):
    model_config = ConfigDict(extra="forbid")

    question_text: str = Field(min_length=1)


class QuestionRead(QuestionBase):
    id: int
    document_id: int
    created_at: datetime


class RetrievedChunkRead(SQLModel):
    chunk_id: int
    chunk_index: int
    content: str
    score: float


class QuestionRetrievalRead(SQLModel):
    question: QuestionRead
    matches: list[RetrievedChunkRead]
