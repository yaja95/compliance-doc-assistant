from fastapi.testclient import TestClient
from sqlmodel import Session

from compliance_doc_assistant.auth import hash_password
from compliance_doc_assistant.database import engine
from compliance_doc_assistant.main import app
from compliance_doc_assistant.models import User
from pdf_fixtures import build_minimal_pdf


def create_user_and_login(
    client: TestClient, username: str, password: str = "some-password"
) -> dict:
    with Session(engine) as session:
        session.add(User(username=username, password_hash=hash_password(password)))
        session.commit()

    login_response = client.post("/auth/login", json={"username": username, "password": password})
    token = login_response.json()["token"]
    # resolve_token_from_request checks the session_token cookie before the
    # Authorization header, and TestClient shares one cookie jar across every
    # login on the same client — without clearing it here, the most recently
    # logged-in user's cookie would silently override the explicit Bearer
    # header used for an earlier-logged-in user in the same test.
    client.cookies.clear()
    return {"Authorization": f"Bearer {token}"}


def test_upload_requires_authentication() -> None:
    with TestClient(app) as client:
        response = client.post("/documents", files={"file": ("policy.txt", b"hello", "text/plain")})

    assert response.status_code == 401


def test_upload_txt_document_success() -> None:
    with TestClient(app) as client:
        headers = create_user_and_login(client, "uploader1")

        response = client.post(
            "/documents",
            files={
                "file": ("policy.txt", b"Section 1: Employees must report incidents.", "text/plain")
            },
            headers=headers,
        )

    assert response.status_code == 201
    body = response.json()
    assert body["filename"] == "policy.txt"
    assert body["source_format"] == "txt"
    assert body["status"] == "chunked"


def test_upload_pdf_document_success() -> None:
    pdf_bytes = build_minimal_pdf("Section 2: Retain records for seven years.")

    with TestClient(app) as client:
        headers = create_user_and_login(client, "uploader2")

        response = client.post(
            "/documents",
            files={"file": ("policy.pdf", pdf_bytes, "application/pdf")},
            headers=headers,
        )

    assert response.status_code == 201
    assert response.json()["source_format"] == "pdf"


def test_upload_rejects_unsupported_file_type() -> None:
    with TestClient(app) as client:
        headers = create_user_and_login(client, "uploader3")

        response = client.post(
            "/documents",
            files={"file": ("policy.docx", b"whatever", "application/octet-stream")},
            headers=headers,
        )

    assert response.status_code == 415


def test_upload_rejects_empty_document() -> None:
    with TestClient(app) as client:
        headers = create_user_and_login(client, "uploader4")

        response = client.post(
            "/documents",
            files={"file": ("blank.txt", b"   ", "text/plain")},
            headers=headers,
        )

    assert response.status_code == 422


def test_upload_rejects_oversized_file() -> None:
    oversized_content = b"a" * (10 * 1024 * 1024 + 1)

    with TestClient(app) as client:
        headers = create_user_and_login(client, "uploader5")

        response = client.post(
            "/documents",
            files={"file": ("huge.txt", oversized_content, "text/plain")},
            headers=headers,
        )

    assert response.status_code == 413


def test_list_documents_returns_only_own_documents() -> None:
    with TestClient(app) as client:
        alice_headers = create_user_and_login(client, "alice-docs")
        bob_headers = create_user_and_login(client, "bob-docs")

        client.post(
            "/documents",
            files={"file": ("alice.txt", b"Alice's compliance policy text.", "text/plain")},
            headers=alice_headers,
        )
        client.post(
            "/documents",
            files={"file": ("bob.txt", b"Bob's compliance policy text.", "text/plain")},
            headers=bob_headers,
        )

        alice_list = client.get("/documents", headers=alice_headers).json()
        bob_list = client.get("/documents", headers=bob_headers).json()

    assert [d["filename"] for d in alice_list] == ["alice.txt"]
    assert [d["filename"] for d in bob_list] == ["bob.txt"]


def test_get_document_detail_includes_chunks() -> None:
    with TestClient(app) as client:
        headers = create_user_and_login(client, "detail-owner")

        upload_response = client.post(
            "/documents",
            files={
                "file": (
                    "policy.txt",
                    b"Section 1: Report incidents within 24 hours.",
                    "text/plain",
                )
            },
            headers=headers,
        )
        document_id = upload_response.json()["id"]

        detail_response = client.get(f"/documents/{document_id}", headers=headers)

    assert detail_response.status_code == 200
    body = detail_response.json()
    assert body["id"] == document_id
    assert len(body["chunks"]) == 1
    assert body["chunks"][0]["content"] == "Section 1: Report incidents within 24 hours."


def test_get_document_returns_404_for_other_users_document() -> None:
    with TestClient(app) as client:
        owner_headers = create_user_and_login(client, "doc-owner")
        other_headers = create_user_and_login(client, "other-user")

        upload_response = client.post(
            "/documents",
            files={"file": ("private.txt", b"Private compliance content.", "text/plain")},
            headers=owner_headers,
        )
        document_id = upload_response.json()["id"]

        response = client.get(f"/documents/{document_id}", headers=other_headers)

    assert response.status_code == 404


def test_get_nonexistent_document_returns_404() -> None:
    with TestClient(app) as client:
        headers = create_user_and_login(client, "nonexistent-doc-user")

        response = client.get("/documents/999999", headers=headers)

    assert response.status_code == 404
