from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlmodel import Session, select

from compliance_doc_assistant.auth import CurrentUser
from compliance_doc_assistant.database import get_session
from compliance_doc_assistant.ingestion import (
    EmptyDocumentError,
    InvalidPdfError,
    UnsupportedFileTypeError,
    ingest_document,
)
from compliance_doc_assistant.models import (
    Chunk,
    ChunkRead,
    Document,
    DocumentDetailRead,
    DocumentRead,
)

SessionDep = Annotated[Session, Depends(get_session)]

MAX_UPLOAD_BYTES = 10 * 1024 * 1024

router = APIRouter(prefix="/documents", tags=["documents"])


def _get_owned_document(session: Session, document_id: int, owner_id: int) -> Document:
    document = session.get(Document, document_id)
    if document is None or document.owner_id != owner_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    return document


@router.post("", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
async def upload_document(
    current_user: CurrentUser,
    session: SessionDep,
    file: UploadFile,
) -> DocumentRead:
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"File exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)}MB upload limit.",
        )

    try:
        document = ingest_document(
            session, current_user.id or 0, file.filename or "upload", content
        )
    except UnsupportedFileTypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(exc)
        ) from exc
    except (EmptyDocumentError, InvalidPdfError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc

    return DocumentRead.model_validate(document)


@router.get("", response_model=list[DocumentRead])
def list_documents(current_user: CurrentUser, session: SessionDep) -> list[DocumentRead]:
    documents = session.exec(
        select(Document)
        .where(Document.owner_id == current_user.id)
        .order_by(Document.uploaded_at.desc())
    ).all()
    return [DocumentRead.model_validate(document) for document in documents]


@router.get("/{document_id}", response_model=DocumentDetailRead)
def get_document(
    document_id: int, current_user: CurrentUser, session: SessionDep
) -> DocumentDetailRead:
    document = _get_owned_document(session, document_id, current_user.id or 0)
    chunks = session.exec(
        select(Chunk).where(Chunk.document_id == document_id).order_by(Chunk.chunk_index)
    ).all()
    return DocumentDetailRead(
        **DocumentRead.model_validate(document).model_dump(),
        chunks=[ChunkRead.model_validate(chunk) for chunk in chunks],
    )
