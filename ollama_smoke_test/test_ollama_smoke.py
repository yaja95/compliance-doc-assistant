"""Live-Ollama smoke test — NOT part of the default `uv run pytest` suite.

This is the one place that exercises real answer generation end-to-end.
There's no funded ANTHROPIC_API_KEY available for this project (a paid API),
so this closes the live-verification gap the same way evalops-dashboard's
ollama_smoke_test did for its LLM judge: a free, self-hostable provider
behind the same GenerationClient interface, run for real against a real
model — not mocked. Run explicitly:

    GENERATION_PROVIDER=ollama OLLAMA_HOST=http://localhost:11434 \
        uv run pytest ollama_smoke_test/ -v

CI's ollama-smoke job is the only place this normally runs, against a real
ollama/ollama service container — see .github/workflows/ci.yml.
"""

import os

GENERATION_PROVIDER = os.environ.get("GENERATION_PROVIDER", "")
if GENERATION_PROVIDER != "ollama":
    raise RuntimeError(
        "ollama_smoke_test requires GENERATION_PROVIDER=ollama; "
        f"got {GENERATION_PROVIDER!r}. This smoke test must not silently fall "
        "back to the Anthropic provider."
    )

from compliance_doc_assistant.generation import get_generation_client  # noqa: E402
from compliance_doc_assistant.models import Chunk  # noqa: E402
from compliance_doc_assistant.retrieval import RetrievedChunk  # noqa: E402


def test_ollama_generates_a_real_answer_from_context() -> None:
    client = get_generation_client()
    assert client.provider == "ollama"

    chunk = Chunk(
        id=1,
        document_id=1,
        chunk_index=0,
        content="Section 4.2: Employees must report safety incidents to compliance "
        "within 24 hours of discovery.",
        token_count=15,
    )
    matches = [RetrievedChunk(chunk=chunk, score=0.9)]

    result = client.generate("How soon must incidents be reported?", matches)

    assert result.answer_text.strip()
    assert result.model
