import os

from sqlmodel import Session, select

from compliance_doc_assistant.auth import hash_password
from compliance_doc_assistant.models import User

SEED_USERNAME = "demo"
SEED_USER_PASSWORD_FALLBACK = "change-me-local-dev-only"  # documented dev-only default


def seed_database(session: Session) -> None:
    ensure_seed_user(session)


def ensure_seed_user(session: Session) -> User:
    user = session.exec(select(User).where(User.username == SEED_USERNAME)).first()
    if user is not None:
        return user

    password = os.getenv("SEED_USER_PASSWORD", SEED_USER_PASSWORD_FALLBACK)
    user = User(username=SEED_USERNAME, password_hash=hash_password(password))
    session.add(user)
    session.commit()
    session.refresh(user)
    return user
