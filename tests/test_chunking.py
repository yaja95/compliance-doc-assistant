import pytest

from compliance_doc_assistant.chunking import split_into_chunks


def test_short_text_returns_one_chunk() -> None:
    chunks = split_into_chunks("one two three", chunk_size_words=500, overlap_words=50)

    assert len(chunks) == 1
    assert chunks[0].content == "one two three"
    assert chunks[0].token_count == 3
    assert chunks[0].chunk_index == 0


def test_empty_text_returns_empty_list() -> None:
    assert split_into_chunks("") == []
    assert split_into_chunks("   ") == []


def test_produces_overlapping_windows() -> None:
    words = [f"w{i}" for i in range(25)]
    text = " ".join(words)

    chunks = split_into_chunks(text, chunk_size_words=10, overlap_words=4)

    assert [c.content for c in chunks] == [
        " ".join(words[0:10]),
        " ".join(words[6:16]),
        " ".join(words[12:22]),
        " ".join(words[18:25]),
    ]


def test_chunk_indices_are_sequential() -> None:
    text = " ".join(f"w{i}" for i in range(25))

    chunks = split_into_chunks(text, chunk_size_words=10, overlap_words=4)

    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))


def test_token_count_matches_word_count_per_chunk() -> None:
    text = " ".join(f"w{i}" for i in range(12))

    chunks = split_into_chunks(text, chunk_size_words=10, overlap_words=2)

    assert all(c.token_count == len(c.content.split()) for c in chunks)


def test_rejects_overlap_greater_than_or_equal_to_chunk_size() -> None:
    with pytest.raises(ValueError, match="overlap_words must be smaller"):
        split_into_chunks("some text", chunk_size_words=10, overlap_words=10)

    with pytest.raises(ValueError, match="overlap_words must be smaller"):
        split_into_chunks("some text", chunk_size_words=10, overlap_words=20)
