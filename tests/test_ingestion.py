import pytest
from sqlmodel import Session, select

from compliance_doc_assistant.database import engine
from compliance_doc_assistant.embeddings import EMBEDDING_DIMENSIONS
from compliance_doc_assistant.ingestion import (
    EmptyDocumentError,
    UnsupportedFileTypeError,
    extract_text,
    ingest_document,
)
from compliance_doc_assistant.models import Chunk, DocumentStatus, User
from pdf_fixtures import build_minimal_pdf


def create_user(username: str) -> int:
    with Session(engine) as session:
        user = User(username=username, password_hash="unused")
        session.add(user)
        session.commit()
        session.refresh(user)
        return user.id or 0


def test_extract_text_from_txt() -> None:
    assert extract_text("policy.txt", b"Hello policy text") == "Hello policy text"


def test_extract_text_from_pdf() -> None:
    pdf_bytes = build_minimal_pdf("Hello Compliance PDF")

    assert extract_text("policy.pdf", pdf_bytes) == "Hello Compliance PDF"


def test_extract_text_rejects_unsupported_extension() -> None:
    with pytest.raises(UnsupportedFileTypeError, match="Unsupported file type '.docx'"):
        extract_text("policy.docx", b"whatever")


def test_ingest_document_persists_document_and_chunks() -> None:
    owner_id = create_user("ingest-owner")
    text = " ".join(f"word{i}" for i in range(1200))

    with Session(engine) as session:
        document = ingest_document(session, owner_id, "big-policy.txt", text.encode("utf-8"))

        assert document.id is not None
        assert document.status == DocumentStatus.EMBEDDED
        assert document.owner_id == owner_id
        assert document.source_format == "txt"

        chunks = session.exec(
            select(Chunk).where(Chunk.document_id == document.id).order_by(Chunk.chunk_index)
        ).all()
        assert len(chunks) > 1
        assert [c.chunk_index for c in chunks] == list(range(len(chunks)))
        assert all(
            c.embedding is not None and len(c.embedding) == EMBEDDING_DIMENSIONS for c in chunks
        )


def test_ingest_document_rejects_empty_text() -> None:
    owner_id = create_user("empty-doc-owner")

    with Session(engine) as session, pytest.raises(EmptyDocumentError):
        ingest_document(session, owner_id, "blank.txt", b"   \n\t  ")
