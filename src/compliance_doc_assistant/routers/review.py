from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from compliance_doc_assistant.auth import CurrentUser
from compliance_doc_assistant.database import get_session
from compliance_doc_assistant.models import (
    ResolveReviewFlagRequest,
    ReviewFlagRead,
    ReviewFlagStatus,
)
from compliance_doc_assistant.review import (
    get_owned_review_flag,
    list_pending_flags,
    resolve_review_flag,
)

SessionDep = Annotated[Session, Depends(get_session)]

router = APIRouter(prefix="/review-flags", tags=["review"])


@router.get("", response_model=list[ReviewFlagRead])
def list_review_flags(current_user: CurrentUser, session: SessionDep) -> list[ReviewFlagRead]:
    flags = list_pending_flags(session, current_user.id or 0)
    return [ReviewFlagRead.model_validate(flag) for flag in flags]


@router.post("/{flag_id}/resolve", response_model=ReviewFlagRead)
def resolve_flag(
    flag_id: int,
    body: ResolveReviewFlagRequest,
    current_user: CurrentUser,
    session: SessionDep,
) -> ReviewFlagRead:
    if body.status == ReviewFlagStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Cannot resolve a flag back to pending status.",
        )

    flag = get_owned_review_flag(session, flag_id, current_user.id or 0)
    if flag is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review flag not found.")

    resolved = resolve_review_flag(session, flag, body.status, current_user.id or 0)
    return ReviewFlagRead.model_validate(resolved)
