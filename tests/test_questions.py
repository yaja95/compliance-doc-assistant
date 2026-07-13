from fastapi.testclient import TestClient
from sqlmodel import Session, select

from compliance_doc_assistant.auth import hash_password
from compliance_doc_assistant.database import engine
from compliance_doc_assistant.main import app
from compliance_doc_assistant.models import Document, DocumentStatus, User


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


def upload_document(client: TestClient, headers: dict, filename: str, content: bytes) -> int:
    response = client.post(
        "/documents",
        files={"file": (filename, content, "text/plain")},
        headers=headers,
    )
    return response.json()["id"]


def test_ask_question_requires_authentication() -> None:
    with TestClient(app) as client:
        response = client.post("/documents/1/questions", json={"question_text": "What is it?"})

    assert response.status_code == 401


def test_ask_question_returns_ranked_matches() -> None:
    with TestClient(app) as client:
        headers = create_user_and_login(client, "asker1")
        document_id = upload_document(
            client,
            headers,
            "policy.txt",
            b"Section 4.2: Employees must report safety incidents within 24 hours. "
            b"Section 9.1: The office holiday party is in December.",
        )

        response = client.post(
            f"/documents/{document_id}/questions",
            json={"question_text": "How soon must incidents be reported?"},
            headers=headers,
        )

    assert response.status_code == 201
    body = response.json()
    assert body["question"]["question_text"] == "How soon must incidents be reported?"
    assert body["question"]["document_id"] == document_id
    assert len(body["matches"]) >= 1
    assert "score" in body["matches"][0]
    assert "content" in body["matches"][0]


def test_ask_question_returns_404_for_other_users_document() -> None:
    with TestClient(app) as client:
        owner_headers = create_user_and_login(client, "question-doc-owner")
        other_headers = create_user_and_login(client, "question-other-user")

        document_id = upload_document(client, owner_headers, "private.txt", b"Private policy text.")

        response = client.post(
            f"/documents/{document_id}/questions",
            json={"question_text": "What does it say?"},
            headers=other_headers,
        )

    assert response.status_code == 404


def test_ask_question_returns_404_for_nonexistent_document() -> None:
    with TestClient(app) as client:
        headers = create_user_and_login(client, "question-nonexistent-doc-user")

        response = client.post(
            "/documents/999999/questions",
            json={"question_text": "What does it say?"},
            headers=headers,
        )

    assert response.status_code == 404


def test_ask_question_rejects_empty_question_text() -> None:
    with TestClient(app) as client:
        headers = create_user_and_login(client, "question-empty-text-user")
        document_id = upload_document(client, headers, "policy.txt", b"Some policy content.")

        response = client.post(
            f"/documents/{document_id}/questions",
            json={"question_text": ""},
            headers=headers,
        )

    assert response.status_code == 422


def test_ask_question_rejects_document_not_yet_embedded() -> None:
    """Every document reachable through the public API is fully "embedded" by
    the time it's persisted (see ingestion.py) — this directly inserts a
    "pending" Document to exercise the status guard, which otherwise has no
    reachable path to test through the API alone.
    """
    with TestClient(app) as client:
        headers = create_user_and_login(client, "question-not-ready-user")

        with Session(engine) as session:
            user = session.exec(
                select(User).where(User.username == "question-not-ready-user")
            ).first()
            document = Document(
                owner_id=user.id,
                filename="pending.txt",
                source_format="txt",
                status=DocumentStatus.PENDING,
            )
            session.add(document)
            session.commit()
            session.refresh(document)
            document_id = document.id

        response = client.post(
            f"/documents/{document_id}/questions",
            json={"question_text": "Is this ready?"},
            headers=headers,
        )

    assert response.status_code == 422
