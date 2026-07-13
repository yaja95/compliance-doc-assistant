from fastapi.testclient import TestClient
from sqlmodel import Session, select

from compliance_doc_assistant.auth import hash_password
from compliance_doc_assistant.database import engine
from compliance_doc_assistant.main import app
from compliance_doc_assistant.models import Answer, Document, Question, User
from compliance_doc_assistant.review import maybe_create_review_flag


def create_user_and_login(
    client: TestClient, username: str, password: str = "some-password"
) -> dict:
    with Session(engine) as session:
        session.add(User(username=username, password_hash=hash_password(password)))
        session.commit()

    login_response = client.post("/auth/login", json={"username": username, "password": password})
    token = login_response.json()["token"]
    client.cookies.clear()
    return {"Authorization": f"Bearer {token}"}


def create_flagged_answer(username: str) -> tuple[int, int]:
    """Returns (owner_id, flag_id) for a freshly created, review-flagged answer."""
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == username)).first()
        owner_id = user.id

        document = Document(owner_id=owner_id, filename="policy.txt", source_format="txt")
        session.add(document)
        session.commit()
        session.refresh(document)

        question = Question(document_id=document.id, asked_by=owner_id, question_text="q?")
        session.add(question)
        session.commit()
        session.refresh(question)

        answer = Answer(
            question_id=question.id,
            answer_text="a.",
            model_used="fake-model",
            needs_review=True,
            confidence_reason="low similarity",
        )
        session.add(answer)
        session.commit()
        session.refresh(answer)

        flag = maybe_create_review_flag(session, answer)

    return owner_id, flag.id


def test_list_review_flags_requires_authentication() -> None:
    with TestClient(app) as client:
        response = client.get("/review-flags")

    assert response.status_code == 401


def test_list_review_flags_returns_only_own_pending_flags() -> None:
    with TestClient(app) as client:
        headers = create_user_and_login(client, "list-flags-owner")
        _, flag_id = create_flagged_answer("list-flags-owner")

        response = client.get("/review-flags", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == flag_id
    assert body[0]["status"] == "pending"


def test_resolve_flag_requires_authentication() -> None:
    with TestClient(app) as client:
        response = client.post("/review-flags/1/resolve", json={"status": "resolved"})

    assert response.status_code == 401


def test_resolve_flag_marks_it_resolved() -> None:
    with TestClient(app) as client:
        headers = create_user_and_login(client, "resolve-flags-owner")
        _, flag_id = create_flagged_answer("resolve-flags-owner")

        response = client.post(
            f"/review-flags/{flag_id}/resolve", json={"status": "resolved"}, headers=headers
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "resolved"
    assert body["reviewed_at"] is not None


def test_resolve_flag_marks_it_dismissed() -> None:
    with TestClient(app) as client:
        headers = create_user_and_login(client, "dismiss-flags-owner")
        _, flag_id = create_flagged_answer("dismiss-flags-owner")

        response = client.post(
            f"/review-flags/{flag_id}/resolve", json={"status": "dismissed"}, headers=headers
        )

    assert response.status_code == 200
    assert response.json()["status"] == "dismissed"


def test_resolve_flag_rejects_pending_status() -> None:
    with TestClient(app) as client:
        headers = create_user_and_login(client, "pending-reject-owner")
        _, flag_id = create_flagged_answer("pending-reject-owner")

        response = client.post(
            f"/review-flags/{flag_id}/resolve", json={"status": "pending"}, headers=headers
        )

    assert response.status_code == 422


def test_resolve_flag_returns_404_for_other_users_flag() -> None:
    with TestClient(app) as client:
        create_user_and_login(client, "flag-owner")
        _, flag_id = create_flagged_answer("flag-owner")
        other_headers = create_user_and_login(client, "flag-other-user")

        response = client.post(
            f"/review-flags/{flag_id}/resolve", json={"status": "resolved"}, headers=other_headers
        )

    assert response.status_code == 404


def test_resolve_flag_returns_404_for_nonexistent_flag() -> None:
    with TestClient(app) as client:
        headers = create_user_and_login(client, "nonexistent-flag-user")

        response = client.post(
            "/review-flags/999999/resolve", json={"status": "resolved"}, headers=headers
        )

    assert response.status_code == 404


def test_resolved_flag_no_longer_appears_in_pending_list() -> None:
    with TestClient(app) as client:
        headers = create_user_and_login(client, "resolved-list-owner")
        _, flag_id = create_flagged_answer("resolved-list-owner")

        client.post(
            f"/review-flags/{flag_id}/resolve", json={"status": "resolved"}, headers=headers
        )
        response = client.get("/review-flags", headers=headers)

    assert response.status_code == 200
    assert response.json() == []
