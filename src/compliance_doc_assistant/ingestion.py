from io import BytesIO
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError
from sqlmodel import Session

from compliance_doc_assistant.chunking import split_into_chunks
from compliance_doc_assistant.models import Chunk, Document, DocumentStatus

SUPPORTED_EXTENSIONS = {".txt", ".pdf"}


class UnsupportedFileTypeError(ValueError):
    pass


class EmptyDocumentError(ValueError):
    pass


class InvalidPdfError(ValueError):
    pass


def extract_text(filename: str, content: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix == ".txt":
        return content.decode("utf-8", errors="replace")
    if suffix == ".pdf":
        return _extract_pdf_text(content)
    raise UnsupportedFileTypeError(
        f"Unsupported file type '{suffix}'. Supported types: "
        f"{', '.join(sorted(SUPPORTED_EXTENSIONS))}."
    )


def _extract_pdf_text(content: bytes) -> str:
    try:
        reader = PdfReader(BytesIO(content))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except PdfReadError as exc:
        raise InvalidPdfError(f"Could not read PDF: {exc}") from exc


def ingest_document(session: Session, owner_id: int, filename: str, content: bytes) -> Document:
    """Extracts text, chunks it, and persists the Document + its Chunks.

    Runs synchronously in-request for v1 (see README's Known Limitations) —
    the caller is responsible for enforcing an upload size limit before this
    is called.
    """
    text = extract_text(filename, content)
    if not text.strip():
        raise EmptyDocumentError(f"'{filename}' contains no extractable text.")

    document = Document(
        owner_id=owner_id,
        filename=filename,
        source_format=Path(filename).suffix.lower().lstrip("."),
        status=DocumentStatus.PENDING,
    )
    session.add(document)
    session.flush()

    drafts = split_into_chunks(text)
    session.add_all(
        [
            Chunk(
                document_id=document.id,
                chunk_index=draft.chunk_index,
                content=draft.content,
                token_count=draft.token_count,
            )
            for draft in drafts
        ]
    )
    document.status = DocumentStatus.CHUNKED
    session.add(document)
    session.commit()
    session.refresh(document)
    return document
