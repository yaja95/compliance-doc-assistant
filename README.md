# compliance-doc-assistant

An AI-powered document review assistant for compliance-heavy financial institution workflows. Upload a policy or regulatory document, ask natural-language questions, and get source-grounded answers with citations back to the originating sections — with low-confidence answers flagged for human review instead of asserted confidently.

## Problem

Financial institutions review large compliance documents manually, creating delays, missed obligations, and inconsistent interpretation.

## Solution

This app allows a user to upload a compliance document, ask natural language questions, receive source-grounded answers with citations, and see a review flag whenever the system isn't confident enough in an answer to assert it without a human check.

## Technical Stack

- **Backend:** Python, FastAPI, SQLModel, Alembic, PostgreSQL + pgvector
- **Embeddings:** local `sentence-transformers` model (`all-MiniLM-L6-v2`)
- **Generation:** Anthropic Claude API by default, with a free local Ollama fallback provider (`GENERATION_PROVIDER=ollama`) behind the same interface
- **Frontend:** Next.js (TypeScript, App Router)
- **Deployment:** Docker Compose (local), Render (planned)

## FDE Relevance

Demonstrates customer workflow discovery, document ingestion, RAG system design, deployment, user-facing UX, and operational risk controls (human-in-the-loop review for low-confidence answers).

## Development

See [AGENTS.md](AGENTS.md) for working norms, [PM_PROTOCOL.md](PM_PROTOCOL.md) for how work is verified and tracked, and [LEDGER.md](LEDGER.md) for the milestone-by-milestone build history.

### Backend

```bash
uv sync                                                                        # install dependencies
docker compose up -d db                                                       # start Postgres + pgvector
uv run alembic upgrade head                                                   # apply migrations
uv run uvicorn --app-dir src compliance_doc_assistant.main:app --reload       # run the API (http://127.0.0.1:8000/docs)
uv run ruff format .                                                          # format
uv run ruff check .                                                          # lint
uv run pytest                                                                # run tests
```

### Frontend

```bash
cd frontend
npm install
npm run dev      # http://localhost:3000
npm run build
```

## Known Limitations

- v1 supports `.txt` and `.pdf` uploads only, up to 10MB per file.
- Chunking is fixed-size (~500 words with ~50-word overlap, not section/heading-aware), which can occasionally split a document mid-clause. "Words" stand in for tokens until a real tokenizer arrives with embeddings.
- Document ingestion runs synchronously in-request; very large PDFs may be slow.
- There is currently only one user account (the seeded `demo` user) — self-service user creation isn't built yet.
- Citations are every chunk retrieved for a question, not chunks the model self-reports actually using — the model is asked to reference them in prose, but citation records are derived mechanically from retrieval, not from structured model output.
- The default Anthropic provider requires `ANTHROPIC_API_KEY` to be set; without it, set `GENERATION_PROVIDER=ollama` and run a local Ollama instance instead (see `docker-compose.yml`'s optional `ollama` service).
- Answers aren't yet flagged for human review when confidence is low — that's the next milestone.
