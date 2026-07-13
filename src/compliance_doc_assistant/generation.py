import os
from dataclasses import dataclass
from typing import Annotated, Protocol

import anthropic
import ollama
from fastapi import Depends, HTTPException, status

from compliance_doc_assistant.retrieval import RetrievedChunk

ANTHROPIC_GENERATION_MODEL_FALLBACK = "claude-haiku-4-5-20251001"
OLLAMA_GENERATION_MODEL_FALLBACK = "qwen2.5:1.5b"
GENERATION_MAX_TOKENS = 1024


@dataclass(frozen=True)
class GenerationResult:
    answer_text: str
    model: str


def build_generation_prompt(question_text: str, chunks: list[RetrievedChunk]) -> str:
    context = "\n\n".join(
        f"[Chunk {match.chunk.chunk_index}]\n{match.chunk.content}" for match in chunks
    )
    return (
        "You are answering a question about a compliance document using ONLY the "
        "excerpts provided below. If the excerpts don't contain enough information "
        "to answer confidently, say so explicitly rather than guessing.\n\n"
        f"Document excerpts:\n{context}\n\n"
        f"Question: {question_text}\n\n"
        "Answer the question directly and concisely, referencing the relevant chunk "
        "numbers where useful."
    )


class GenerationClient(Protocol):
    provider: str

    def generate(self, question_text: str, chunks: list[RetrievedChunk]) -> GenerationResult: ...


class AnthropicGenerationClient:
    provider = "anthropic"

    def __init__(self) -> None:
        self._client: anthropic.Anthropic | None = None

    def _client_or_503(self) -> anthropic.Anthropic:
        if self._client is None:
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="ANTHROPIC_API_KEY is not configured; answer generation is unavailable.",
                )
            self._client = anthropic.Anthropic(api_key=api_key)
        return self._client

    def generate(self, question_text: str, chunks: list[RetrievedChunk]) -> GenerationResult:
        client = self._client_or_503()
        model = os.getenv("ANTHROPIC_GENERATION_MODEL", ANTHROPIC_GENERATION_MODEL_FALLBACK)
        try:
            message = client.messages.create(
                model=model,
                max_tokens=GENERATION_MAX_TOKENS,
                messages=[
                    {"role": "user", "content": build_generation_prompt(question_text, chunks)}
                ],
            )
        except anthropic.APIError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Answer generation request failed: {exc}",
            ) from exc

        text_block = next(
            (block for block in message.content if getattr(block, "type", None) == "text"), None
        )
        if text_block is None:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Answer generation did not return any text.",
            )
        return GenerationResult(answer_text=text_block.text, model=message.model)


class OllamaGenerationClient:
    provider = "ollama"

    def __init__(self) -> None:
        self._client: ollama.Client | None = None

    def _get_client(self) -> ollama.Client:
        if self._client is None:
            host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
            self._client = ollama.Client(host=host)
        return self._client

    def generate(self, question_text: str, chunks: list[RetrievedChunk]) -> GenerationResult:
        client = self._get_client()
        model = os.getenv("OLLAMA_GENERATION_MODEL", OLLAMA_GENERATION_MODEL_FALLBACK)
        try:
            response = client.chat(
                model=model,
                messages=[
                    {"role": "user", "content": build_generation_prompt(question_text, chunks)}
                ],
            )
        except ConnectionError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Ollama is not reachable; answer generation is unavailable.",
            ) from exc
        except (ollama.ResponseError, ollama.RequestError) as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Answer generation request failed: {exc}",
            ) from exc

        content = response.message.content
        if not content:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Answer generation did not return any text.",
            )
        return GenerationResult(answer_text=content, model=response.model)


def get_generation_client() -> GenerationClient:
    if os.getenv("GENERATION_PROVIDER", "anthropic").lower() == "ollama":
        return OllamaGenerationClient()
    return AnthropicGenerationClient()


GenerationClientDep = Annotated[GenerationClient, Depends(get_generation_client)]
