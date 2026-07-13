import os
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from compliance_doc_assistant.auth import create_session, hash_password
from compliance_doc_assistant.database import engine
from compliance_doc_assistant.main import app
from compliance_doc_assistant.models import User
from compliance_doc_assistant.seed import SEED_USER_PASSWORD_FALLBACK, SEED_USERNAME


def create_real_user(username: str, password: str) -> None:
    with Session(engine) as session:
        user = User(username=username, password_hash=hash_password(password))
        session.add(user)
        session.commit()


def test_login_with_valid_credentials_succeeds() -> None:
    create_real_user("alice", "correct-horse-battery")

    with TestClient(app) as client:
        response = client.post(
            "/auth/login", json={"username": "alice", "password": "correct-horse-battery"}
        )

    assert response.status_code == 200
    body = response.json()
    assert "token" in body
    assert body["user"]["username"] == "alice"
    set_cookie = response.headers.get("set-cookie", "")
    assert "session_token=" in set_cookie
    assert "httponly" in set_cookie.lower()
    assert "samesite=lax" in set_cookie.lower()


def test_login_with_wrong_password_returns_generic_error() -> None:
    create_real_user("bob", "correct-password")

    with TestClient(app) as client:
        response = client.post(
            "/auth/login", json={"username": "bob", "password": "wrong-password"}
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid username or password."


def test_login_with_nonexistent_username_returns_same_generic_error() -> None:
    create_real_user("carol", "correct-password")

    with TestClient(app) as client:
        wrong_password = client.post(
            "/auth/login", json={"username": "carol", "password": "wrong-password"}
        )
        nonexistent_user = client.post(
            "/auth/login", json={"username": "no-such-user", "password": "anything"}
        )

    assert wrong_password.status_code == 401
    assert nonexistent_user.status_code == 401
    assert wrong_password.json()["detail"] == nonexistent_user.json()["detail"]


def test_logout_invalidates_session() -> None:
    create_real_user("dave", "some-password")

    with TestClient(app) as client:
        login_response = client.post(
            "/auth/login", json={"username": "dave", "password": "some-password"}
        )
        token = login_response.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        before_logout = client.get("/me", headers=headers)
        client.post("/auth/logout", headers=headers)
        after_logout = client.get("/me", headers=headers)

    assert before_logout.status_code == 200
    assert after_logout.status_code == 401


def test_protected_route_without_auth_returns_401() -> None:
    with TestClient(app) as client:
        response = client.get("/me")

    assert response.status_code == 401


def test_session_token_expires() -> None:
    create_real_user("frank", "frank-password")

    with TestClient(app) as client:
        with Session(engine) as session:
            user = session.exec(select(User).where(User.username == "frank")).first()
            expired_session = create_session(user, session)
            expired_session.expires_at = datetime.now(UTC) - timedelta(days=1)
            session.add(expired_session)
            session.commit()
            token = expired_session.token

        response = client.get("/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


def test_demo_user_is_seeded_and_can_log_in() -> None:
    password = os.getenv("SEED_USER_PASSWORD", SEED_USER_PASSWORD_FALLBACK)

    with TestClient(app) as client:
        response = client.post(
            "/auth/login",
            json={"username": SEED_USERNAME, "password": password},
        )

    assert response.status_code == 200
    assert response.json()["user"]["username"] == SEED_USERNAME
