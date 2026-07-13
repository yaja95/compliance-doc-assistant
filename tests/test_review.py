from sqlmodel import Session

from compliance_doc_assistant.auth import hash_password
from compliance_doc_assistant.database import engine
from compliance_doc_assistant.models import (
    Answer,
    Document,
    Question,
    ReviewFlagStatus,
    User,
)
from compliance_doc_assistant.review import (
    get_owned_review_flag,
    list_pending_flags,
    maybe_create_review_flag,
    resolve_review_flag,
)


def create_user(username: str) -> int:
    with Session(engine) as session:
        user = User(username=username, password_hash=hash_password("password123"))
        session.add(user)
        session.commit()
        session.refresh(user)
        return user.id or 0


def create_answer(owner_id: int, needs_review: bool, reason: str | None = None) -> int:
    with Session(engine) as session:
        document = Document(owner_id=owner_id, filename="policy.txt", source_format="txt")
        session.add(document)
        session.commit()
        session.refresh(document)

        question = Question(document_id=document.id, asked_by=owner_id, question_text="q?")
        session.add(question)
        session.commit()
        session.refresh(question)

        answer = Answer(
            question_id=question.id,
            answer_text="a.",
            model_used="fake-model",
            needs_review=needs_review,
            confidence_reason=reason,
        )
        session.add(answer)
        session.commit()
        session.refresh(answer)
        return answer.id or 0


def test_maybe_create_review_flag_creates_flag_when_needed() -> None:
    owner_id = create_user("review-owner-1")
    answer_id = create_answer(owner_id, needs_review=True, reason="low similarity")

    with Session(engine) as session:
        answer = session.get(Answer, answer_id)
        flag = maybe_create_review_flag(session, answer)

    assert flag is not None
    assert flag.answer_id == answer_id
    assert flag.reason == "low similarity"
    assert flag.status == ReviewFlagStatus.PENDING


def test_maybe_create_review_flag_returns_none_when_not_needed() -> None:
    owner_id = create_user("review-owner-2")
    answer_id = create_answer(owner_id, needs_review=False)

    with Session(engine) as session:
        answer = session.get(Answer, answer_id)
        flag = maybe_create_review_flag(session, answer)

    assert flag is None


def test_list_pending_flags_scoped_to_owner() -> None:
    owner_id = create_user("review-owner-3")
    other_owner_id = create_user("review-owner-4")
    answer_id = create_answer(owner_id, needs_review=True, reason="ambiguous")
    other_answer_id = create_answer(other_owner_id, needs_review=True, reason="ambiguous")

    with Session(engine) as session:
        answer = session.get(Answer, answer_id)
        maybe_create_review_flag(session, answer)
        other_answer = session.get(Answer, other_answer_id)
        maybe_create_review_flag(session, other_answer)

        owner_flags = list_pending_flags(session, owner_id)

    assert len(owner_flags) == 1
    assert owner_flags[0].answer_id == answer_id


def test_get_owned_review_flag_returns_none_for_other_owner() -> None:
    owner_id = create_user("review-owner-5")
    other_owner_id = create_user("review-owner-6")
    answer_id = create_answer(owner_id, needs_review=True, reason="low similarity")

    with Session(engine) as session:
        answer = session.get(Answer, answer_id)
        flag = maybe_create_review_flag(session, answer)

        found_for_owner = get_owned_review_flag(session, flag.id, owner_id)
        found_for_other = get_owned_review_flag(session, flag.id, other_owner_id)

    assert found_for_owner is not None
    assert found_for_other is None


def test_resolve_review_flag_sets_status_and_reviewer() -> None:
    owner_id = create_user("review-owner-7")
    answer_id = create_answer(owner_id, needs_review=True, reason="low similarity")

    with Session(engine) as session:
        answer = session.get(Answer, answer_id)
        flag = maybe_create_review_flag(session, answer)

        resolved = resolve_review_flag(session, flag, ReviewFlagStatus.RESOLVED, owner_id)

    assert resolved.status == ReviewFlagStatus.RESOLVED
    assert resolved.reviewed_by == owner_id
    assert resolved.reviewed_at is not None
