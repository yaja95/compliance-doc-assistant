from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from compliance_doc_assistant.auth import hash_password
from compliance_doc_assistant.confidence import ConfidenceResult
from compliance_doc_assistant.database import engine
from compliance_doc_assistant.generation import GenerationResult, get_generation_client
from compliance_doc_assistant.main import app
from compliance_doc_assistant.models import Document, DocumentStatus, User
from compliance_doc_assistant.retrieval import RetrievedChunk

FAKE_ANSWER_TEXT = "Incidents must be reported within 24 hours (stub answer)."
FAKE_ANSWER_MODEL = "fake-model"


class FakeGenerationClient:
    provider = "fake-provider"

    def generate(self, question_text: str, chunks: list[RetrievedChunk]) -> GenerationResult:
        del question_text, chunks
        return GenerationResult(answer_text=FAKE_ANSWER_TEXT, model=FAKE_ANSWER_MODEL)


@pytest.fixture(autouse=True)
def _default_generation_client() -> Generator[None]:
    """Stubs get_generation_client for every test in this file so none reach
    the network (Anthropic or Ollama) by default.
    """
    app.dependency_overrides[get_generation_client] = lambda: FakeGenerationClient()
    yield
    app.dependency_overrides.pop(get_generation_client, None)


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


def test_ask_question_returns_generated_answer_with_citations() -> None:
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
    assert body["answer"]["answer_text"] == FAKE_ANSWER_TEXT
    assert body["answer"]["model_used"] == FAKE_ANSWER_MODEL
    assert len(body["answer"]["citations"]) >= 1
    citation = body["answer"]["citations"][0]
    assert citation["rank"] == 0
    assert "content" in citation
    assert "relevance_score" in citation


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


def test_low_confidence_answer_is_flagged_and_creates_review_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "compliance_doc_assistant.routers.questions.assess_confidence",
        lambda scores: ConfidenceResult(needs_review=True, reason="forced for test"),
    )

    with TestClient(app) as client:
        headers = create_user_and_login(client, "low-confidence-user")
        document_id = upload_document(client, headers, "policy.txt", b"Some policy content.")

        ask_response = client.post(
            f"/documents/{document_id}/questions",
            json={"question_text": "What does it say?"},
            headers=headers,
        )
        flags_response = client.get("/review-flags", headers=headers)

    assert ask_response.status_code == 201
    answer = ask_response.json()["answer"]
    assert answer["needs_review"] is True
    assert answer["confidence_reason"] == "forced for test"

    assert flags_response.status_code == 200
    flags = flags_response.json()
    assert len(flags) == 1
    assert flags[0]["reason"] == "forced for test"
    assert flags[0]["status"] == "pending"


def test_high_confidence_answer_is_not_flagged(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "compliance_doc_assistant.routers.questions.assess_confidence",
        lambda scores: ConfidenceResult(needs_review=False, reason=None),
    )

    with TestClient(app) as client:
        headers = create_user_and_login(client, "high-confidence-user")
        document_id = upload_document(client, headers, "policy.txt", b"Some policy content.")

        ask_response = client.post(
            f"/documents/{document_id}/questions",
            json={"question_text": "What does it say?"},
            headers=headers,
        )
        flags_response = client.get("/review-flags", headers=headers)

    assert ask_response.status_code == 201
    answer = ask_response.json()["answer"]
    assert answer["needs_review"] is False
    assert answer["confidence_reason"] is None

    assert flags_response.status_code == 200
    assert flags_response.json() == []
