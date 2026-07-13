from dataclasses import dataclass

from sqlmodel import Session, select

from compliance_doc_assistant.models import Chunk

DEFAULT_TOP_K = 5


@dataclass
class RetrievedChunk:
    chunk: Chunk
    score: float


def retrieve_relevant_chunks(
    session: Session,
    document_id: int,
    query_embedding: list[float],
    top_k: int = DEFAULT_TOP_K,
) -> list[RetrievedChunk]:
    """Nearest-neighbor search over one document's chunks via pgvector's
    cosine-distance operator (uses the HNSW index). `score` is cosine
    similarity (1 - distance), so higher is more relevant.
    """
    distance = Chunk.embedding.cosine_distance(query_embedding)
    rows = session.exec(
        select(Chunk, distance.label("distance"))
        .where(Chunk.document_id == document_id)
        .where(Chunk.embedding.is_not(None))
        .order_by(distance)
        .limit(top_k)
    ).all()
    return [RetrievedChunk(chunk=chunk, score=1 - dist) for chunk, dist in rows]
