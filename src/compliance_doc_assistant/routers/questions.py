from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from compliance_doc_assistant.auth import CurrentUser
from compliance_doc_assistant.database import get_session
from compliance_doc_assistant.embeddings import embed_texts
from compliance_doc_assistant.generation import GenerationClientDep, GenerationResult
from compliance_doc_assistant.models import (
    Answer,
    AnswerCitation,
    AnswerCitationRead,
    AnswerRead,
    AnswerWithCitationsRead,
    DocumentStatus,
    Question,
    QuestionAnswerRead,
    QuestionCreate,
    QuestionRead,
)
from compliance_doc_assistant.retrieval import RetrievedChunk, retrieve_relevant_chunks
from compliance_doc_assistant.routers.documents import get_owned_document

SessionDep = Annotated[Session, Depends(get_session)]

NO_CONTEXT_ANSWER = "I don't have enough information in this document to answer that question."

router = APIRouter(prefix="/documents", tags=["questions"])


@router.post(
    "/{document_id}/questions",
    response_model=QuestionAnswerRead,
    status_code=status.HTTP_201_CREATED,
)
def ask_question(
    document_id: int,
    question_create: QuestionCreate,
    current_user: CurrentUser,
    session: SessionDep,
    generation_client: GenerationClientDep,
) -> QuestionAnswerRead:
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

    result = _generate_answer(generation_client, question_create.question_text, matches)

    answer = Answer(
        question_id=question.id or 0,
        answer_text=result.answer_text,
        model_used=result.model,
    )
    session.add(answer)
    session.flush()

    session.add_all(
        [
            AnswerCitation(
                answer_id=answer.id,
                chunk_id=match.chunk.id or 0,
                relevance_score=match.score,
                rank=rank,
            )
            for rank, match in enumerate(matches)
        ]
    )
    session.commit()
    session.refresh(answer)

    return QuestionAnswerRead(
        question=QuestionRead.model_validate(question),
        answer=AnswerWithCitationsRead(
            **AnswerRead.model_validate(answer).model_dump(),
            citations=[
                AnswerCitationRead(
                    chunk_id=match.chunk.id or 0,
                    chunk_index=match.chunk.chunk_index,
                    content=match.chunk.content,
                    relevance_score=match.score,
                    rank=rank,
                )
                for rank, match in enumerate(matches)
            ],
        ),
    )


def _generate_answer(
    generation_client: GenerationClientDep,
    question_text: str,
    matches: list[RetrievedChunk],
) -> GenerationResult:
    if not matches:
        return GenerationResult(answer_text=NO_CONTEXT_ANSWER, model="none")
    return generation_client.generate(question_text, matches)
