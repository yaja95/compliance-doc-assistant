from dataclasses import dataclass

CHUNK_SIZE_WORDS = 500
CHUNK_OVERLAP_WORDS = 50


@dataclass
class ChunkDraft:
    chunk_index: int
    content: str
    token_count: int


def split_into_chunks(
    text: str,
    chunk_size_words: int = CHUNK_SIZE_WORDS,
    overlap_words: int = CHUNK_OVERLAP_WORDS,
) -> list[ChunkDraft]:
    """Splits text into fixed-size, overlapping windows of whitespace-separated
    words. "Words" stand in for tokens here — there's no tokenizer wired up
    until embeddings arrive (Milestone 4), and this approximation is close
    enough for v1 chunk sizing.
    """
    if overlap_words >= chunk_size_words:
        raise ValueError("overlap_words must be smaller than chunk_size_words.")

    words = text.split()
    if not words:
        return []

    stride = chunk_size_words - overlap_words
    drafts = []
    start = 0
    chunk_index = 0
    while start < len(words):
        end = min(start + chunk_size_words, len(words))
        window = words[start:end]
        drafts.append(
            ChunkDraft(
                chunk_index=chunk_index,
                content=" ".join(window),
                token_count=len(window),
            )
        )
        chunk_index += 1
        # Stop once a window reaches the end of the text — otherwise the next
        # stride step would still be < len(words) and emit a tiny, mostly
        # duplicate trailing chunk that overlaps almost entirely with this one.
        if end == len(words):
            break
        start += stride

    return drafts
