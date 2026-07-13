from datetime import UTC, datetime

from pydantic import ConfigDict
from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


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
