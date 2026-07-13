from sqlmodel import Session

from compliance_doc_assistant.database import engine
from compliance_doc_assistant.embeddings import EMBEDDING_DIMENSIONS
from compliance_doc_assistant.models import Chunk, Document, User
from compliance_doc_assistant.retrieval import retrieve_relevant_chunks


def _unit_vector(index: int) -> list[float]:
    vector = [0.0] * EMBEDDING_DIMENSIONS
    vector[index] = 1.0
    return vector


def create_user(username: str) -> int:
    with Session(engine) as session:
        user = User(username=username, password_hash="unused")
        session.add(user)
        session.commit()
        session.refresh(user)
        return user.id or 0


def create_document(owner_id: int, filename: str) -> int:
    with Session(engine) as session:
        document = Document(owner_id=owner_id, filename=filename, source_format="txt")
        session.add(document)
        session.commit()
        session.refresh(document)
        return document.id or 0


def test_retrieve_relevant_chunks_orders_by_similarity() -> None:
    owner_id = create_user("retrieval-owner-1")
    document_id = create_document(owner_id, "policy.txt")

    with Session(engine) as session:
        session.add_all(
            [
                Chunk(
                    document_id=document_id,
                    chunk_index=0,
                    content="matches the query exactly",
                    token_count=4,
                    embedding=_unit_vector(0),
                ),
                Chunk(
                    document_id=document_id,
                    chunk_index=1,
                    content="orthogonal to the query",
                    token_count=4,
                    embedding=_unit_vector(1),
                ),
            ]
        )
        session.commit()

        results = retrieve_relevant_chunks(session, document_id, _unit_vector(0), top_k=2)

    assert [r.chunk.content for r in results] == [
        "matches the query exactly",
        "orthogonal to the query",
    ]
    assert results[0].score > results[1].score
    assert results[0].score == 1.0
    assert results[1].score == 0.0


def test_retrieve_relevant_chunks_scoped_to_document() -> None:
    owner_id = create_user("retrieval-owner-2")
    document_a = create_document(owner_id, "a.txt")
    document_b = create_document(owner_id, "b.txt")

    with Session(engine) as session:
        session.add(
            Chunk(
                document_id=document_a,
                chunk_index=0,
                content="belongs to document A",
                token_count=4,
                embedding=_unit_vector(0),
            )
        )
        session.add(
            Chunk(
                document_id=document_b,
                chunk_index=0,
                content="belongs to document B",
                token_count=4,
                embedding=_unit_vector(0),
            )
        )
        session.commit()

        results = retrieve_relevant_chunks(session, document_a, _unit_vector(0))

    assert len(results) == 1
    assert results[0].chunk.content == "belongs to document A"


def test_retrieve_relevant_chunks_respects_top_k() -> None:
    owner_id = create_user("retrieval-owner-3")
    document_id = create_document(owner_id, "many-chunks.txt")

    with Session(engine) as session:
        session.add_all(
            [
                Chunk(
                    document_id=document_id,
                    chunk_index=i,
                    content=f"chunk {i}",
                    token_count=2,
                    embedding=_unit_vector(i % EMBEDDING_DIMENSIONS),
                )
                for i in range(5)
            ]
        )
        session.commit()

        results = retrieve_relevant_chunks(session, document_id, _unit_vector(0), top_k=2)

    assert len(results) == 2


def test_retrieve_relevant_chunks_excludes_null_embeddings() -> None:
    owner_id = create_user("retrieval-owner-4")
    document_id = create_document(owner_id, "partial.txt")

    with Session(engine) as session:
        session.add(
            Chunk(
                document_id=document_id,
                chunk_index=0,
                content="has an embedding",
                token_count=3,
                embedding=_unit_vector(0),
            )
        )
        session.add(
            Chunk(
                document_id=document_id,
                chunk_index=1,
                content="missing an embedding",
                token_count=3,
                embedding=None,
            )
        )
        session.commit()

        results = retrieve_relevant_chunks(session, document_id, _unit_vector(0))

    assert len(results) == 1
    assert results[0].chunk.content == "has an embedding"
