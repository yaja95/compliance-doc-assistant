from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from compliance_doc_assistant.auth import CurrentUser
from compliance_doc_assistant.database import get_session
from compliance_doc_assistant.embeddings import embed_texts
from compliance_doc_assistant.models import (
    DocumentStatus,
    Question,
    QuestionCreate,
    QuestionRead,
    QuestionRetrievalRead,
    RetrievedChunkRead,
)
from compliance_doc_assistant.retrieval import retrieve_relevant_chunks
from compliance_doc_assistant.routers.documents import get_owned_document

SessionDep = Annotated[Session, Depends(get_session)]

router = APIRouter(prefix="/documents", tags=["questions"])


@router.post(
    "/{document_id}/questions",
    response_model=QuestionRetrievalRead,
    status_code=status.HTTP_201_CREATED,
)
def ask_question(
    document_id: int,
    question_create: QuestionCreate,
    current_user: CurrentUser,
    session: SessionDep,
) -> QuestionRetrievalRead:
    document = get_owned_document(session, document_id, current_user.id or 0)
    if document.status != DocumentStatus.EMBEDDED:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Document is not ready for questions yet (status: {document.status}).",
        )

    question = Question(
        document_id=document_id,
        asked_by=current_user.id or 0,
        question_text=question_create.question_text,
    )
    session.add(question)
    session.commit()
    session.refresh(question)

    query_embedding = embed_texts([question_create.question_text])[0]
    matches = retrieve_relevant_chunks(session, document_id, query_embedding)

    return QuestionRetrievalRead(
        question=QuestionRead.model_validate(question),
        matches=[
            RetrievedChunkRead(
                chunk_id=match.chunk.id or 0,
                chunk_index=match.chunk.chunk_index,
                content=match.chunk.content,
                score=match.score,
            )
            for match in matches
        ],
    )
