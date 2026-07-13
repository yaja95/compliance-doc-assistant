from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import ConfigDict
from sqlmodel import Session, SQLModel

from compliance_doc_assistant.auth import (
    SESSION_LIFETIME,
    CurrentUser,
    authenticate_user,
    create_session,
    invalidate_session,
    resolve_token_from_request,
)
from compliance_doc_assistant.database import get_session
from compliance_doc_assistant.models import UserRead

SessionDep = Annotated[Session, Depends(get_session)]

INVALID_CREDENTIALS_DETAIL = "Invalid username or password."


class LoginRequest(SQLModel):
    model_config = ConfigDict(extra="forbid")

    username: str
    password: str


class LoginResponse(SQLModel):
    token: str
    user: UserRead


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(
    login_request: LoginRequest,
    response: Response,
    session: SessionDep,
) -> LoginResponse:
    user = authenticate_user(login_request.username, login_request.password, session)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=INVALID_CREDENTIALS_DETAIL,
        )

    auth_session = create_session(user, session)
    response.set_cookie(
        key="session_token",
        value=auth_session.token,
        httponly=True,
        samesite="lax",
        max_age=int(SESSION_LIFETIME.total_seconds()),
    )
    return LoginResponse(
        token=auth_session.token,
        user=UserRead(id=user.id or 0, username=user.username, created_at=user.created_at),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    session: SessionDep,
    token: Annotated[str | None, Depends(resolve_token_from_request)],
) -> None:
    if token:
        invalidate_session(session, token)
    response.delete_cookie("session_token")


me_router = APIRouter(tags=["auth"])


@me_router.get("/me", response_model=UserRead)
def read_current_user(current_user: CurrentUser) -> UserRead:
    return UserRead(
        id=current_user.id or 0,
        username=current_user.username,
        created_at=current_user.created_at,
    )
