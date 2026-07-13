import pytest
from fastapi import HTTPException

from compliance_doc_assistant.generation import (
    AnthropicGenerationClient,
    OllamaGenerationClient,
    build_generation_prompt,
    get_generation_client,
)
from compliance_doc_assistant.models import Chunk
from compliance_doc_assistant.retrieval import RetrievedChunk
from compliance_doc_assistant.routers.questions import NO_CONTEXT_ANSWER, _generate_answer


def make_match(chunk_index: int, content: str, score: float) -> RetrievedChunk:
    chunk = Chunk(
        id=chunk_index + 1,
        document_id=1,
        chunk_index=chunk_index,
        content=content,
        token_count=len(content.split()),
    )
    return RetrievedChunk(chunk=chunk, score=score)


def test_build_generation_prompt_includes_chunks_and_question() -> None:
    matches = [make_match(0, "Employees must report incidents within 24 hours.", 0.9)]

    prompt = build_generation_prompt("How soon must incidents be reported?", matches)

    assert "How soon must incidents be reported?" in prompt
    assert "Employees must report incidents within 24 hours." in prompt
    assert "[Chunk 0]" in prompt


def test_anthropic_generation_client_raises_503_when_no_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    with pytest.raises(HTTPException) as exc_info:
        AnthropicGenerationClient().generate("question", [make_match(0, "content", 0.5)])

    assert exc_info.value.status_code == 503


def test_ollama_generation_client_raises_503_when_unreachable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OLLAMA_HOST", "http://127.0.0.1:11434")

    with pytest.raises(HTTPException) as exc_info:
        OllamaGenerationClient().generate("question", [make_match(0, "content", 0.5)])

    assert exc_info.value.status_code in (502, 503)


def test_get_generation_client_defaults_to_anthropic(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GENERATION_PROVIDER", raising=False)

    assert isinstance(get_generation_client(), AnthropicGenerationClient)


def test_get_generation_client_selects_ollama_when_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GENERATION_PROVIDER", "ollama")

    assert isinstance(get_generation_client(), OllamaGenerationClient)


def test_generate_answer_with_no_matches_returns_fallback_without_calling_client() -> None:
    class ExplodingClient:
        provider = "exploding"

        def generate(self, question_text: str, chunks: list[RetrievedChunk]):
            raise AssertionError("should not be called when there are no matches")

    result = _generate_answer(ExplodingClient(), "any question", [])

    assert result.answer_text == NO_CONTEXT_ANSWER
    assert result.model == "none"
