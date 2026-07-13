from datetime import UTC, datetime

from sqlmodel import Session, select

from compliance_doc_assistant.models import (
    Answer,
    Document,
    Question,
    ReviewFlag,
    ReviewFlagStatus,
)


def maybe_create_review_flag(session: Session, answer: Answer) -> ReviewFlag | None:
    if not answer.needs_review:
        return None
    flag = ReviewFlag(answer_id=answer.id or 0, reason=answer.confidence_reason or "")
    session.add(flag)
    session.commit()
    session.refresh(flag)
    return flag


def list_pending_flags(session: Session, owner_id: int) -> list[ReviewFlag]:
    return list(
        session.exec(
            select(ReviewFlag)
            .join(Answer, Answer.id == ReviewFlag.answer_id)
            .join(Question, Question.id == Answer.question_id)
            .join(Document, Document.id == Question.document_id)
            .where(Document.owner_id == owner_id)
            .where(ReviewFlag.status == ReviewFlagStatus.PENDING)
            .order_by(ReviewFlag.created_at)
        ).all()
    )


def get_owned_review_flag(session: Session, flag_id: int, owner_id: int) -> ReviewFlag | None:
    return session.exec(
        select(ReviewFlag)
        .join(Answer, Answer.id == ReviewFlag.answer_id)
        .join(Question, Question.id == Answer.question_id)
        .join(Document, Document.id == Question.document_id)
        .where(ReviewFlag.id == flag_id)
        .where(Document.owner_id == owner_id)
    ).first()


def resolve_review_flag(
    session: Session,
    flag: ReviewFlag,
    new_status: ReviewFlagStatus,
    reviewer_id: int,
) -> ReviewFlag:
    flag.status = new_status
    flag.reviewed_by = reviewer_id
    flag.reviewed_at = datetime.now(UTC)
    session.add(flag)
    session.commit()
    session.refresh(flag)
    return flag
