# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

@AGENTS.md

## Commands

### Backend

```bash
uv sync                                                                      # install dependencies
docker compose up -d db                                                     # start Postgres + pgvector
uv run alembic upgrade head                                                 # apply migrations (required before first run)
uv run uvicorn --app-dir src compliance_doc_assistant.main:app --reload     # run the API (http://127.0.0.1:8000/docs)
uv run ruff format .                                                        # format
uv run ruff check .                                                        # lint
uv run pytest                                                               # run all tests
```

### Frontend

```bash
cd frontend
npm install
npm run dev      # http://localhost:3000
npm run lint
npm run build
```

CI (`.github/workflows/ci.yml`) has three jobs: `backend-test` (spins up a `pgvector/pgvector:pg16` service container, creates a separate `compliance_doc_assistant_test` database, then runs `ruff format --check`, `ruff check`, `alembic upgrade head`, `pytest` — with embeddings stubbed, see below), `pgvector-smoke` (its own `pgvector/pgvector:pg16` service container, runs migrations, then `pytest pgvector_smoke_test/ -v` — the one place that loads the real `sentence-transformers` model and runs a real cosine-distance nearest-neighbor query, mirroring evalops-dashboard's `postgres_smoke_test`/`ollama_smoke_test` pattern), and `frontend` (`npm ci`, `npm run lint`, `npm run build`).

`tests/conftest.py` has an autouse `_stub_embeddings` fixture that monkeypatches `compliance_doc_assistant.ingestion.embed_texts` with a deterministic fake (distinct vectors per distinct text, no real model load) — this keeps the default `pytest` run fast and network-free. `pgvector_smoke_test/` lives outside `tests/` specifically so this stub never applies there.

Unlike `evalops-dashboard`, there is **no SQLite fallback** — `pgvector`/`vector` columns require a real Postgres with the extension enabled, so `docker compose up -d db` (or CI's service container) is required before running migrations or tests at all. `docker/init-test-db.sql` creates the dedicated `compliance_doc_assistant_test` database (and enables the extension on it) automatically on first container startup.

Database URL is configurable via `COMPLIANCE_DATABASE_URL` (defaults to a local `compliance_doc_assistant` Postgres database matching `docker-compose.yml`); `COMPLIANCE_TEST_DATABASE_URL` (defaults to `compliance_doc_assistant_test`) is what `tests/conftest.py` forces the app to use, guarded by a `RuntimeError` if the resolved database name doesn't contain `test`.

## Architecture

FastAPI + SQLModel app under `src/compliance_doc_assistant/`, mirroring evalops-dashboard's flat-modules-plus-routers style:

- `database.py` — single SQLAlchemy `engine`, built from `COMPLIANCE_DATABASE_URL`. No SQLite branching (unlike evalops-dashboard) since Postgres is mandatory here.
- `models.py` — all SQLModel table models plus their `*Create`/`*Read` DTOs, colocated. `User`/`AuthSession` (Milestone 2), `Document`/`Chunk` (Milestone 3; `Chunk.embedding` added in Milestone 4). `DocumentStatus` and `ChunkRead`/`DocumentDetailRead` DTOs live here too. `Document.status` is forced to a plain `sa.String(length=20)` rather than a native Postgres ENUM, same rationale as evalops-dashboard's `User.role` — new status values need no migration (Milestone 4 added `EMBEDDED` as the new terminal success status this way, no migration required). `Chunk.embedding` (`pgvector.sqlalchemy.Vector(EMBEDDING_DIMENSIONS)`) is never client-submittable — lives only on `Chunk`, not `ChunkBase`/`ChunkRead`, same server-controlled-results placement as `Document.status`.
- `auth.py` — session-based auth (bcrypt hashing, opaque `secrets.token_urlsafe` tokens, cookie or `Authorization: Bearer`), direct port of evalops-dashboard's pattern minus RBAC/rate-limiting (deliberately deferred, see `LEDGER.md` Milestone 2).
- `chunking.py` — pure function `split_into_chunks(text, chunk_size_words, overlap_words) -> list[ChunkDraft]`. No DB, no model, no I/O. "Words" (whitespace-split) stand in for tokens — there's still no real tokenizer wired up (the sentence-transformers model does its own tokenization internally, but chunk sizing doesn't call into it). Stops emitting windows once one reaches the end of the text, rather than always advancing by a fixed stride — otherwise a stride that doesn't evenly divide the text length produces a tiny, almost-entirely-duplicate trailing chunk (caught by `test_produces_overlapping_windows` during Milestone 3).
- `embeddings.py` — `EMBEDDING_DIMENSIONS = 384` (matches the migration's `Vector(384)` column, and `all-MiniLM-L6-v2`'s real output size). `_get_model()` lazily loads the `sentence-transformers` model behind an `lru_cache(maxsize=1)` singleton — never at import time. `embed_texts(texts) -> list[list[float]]` is the only public entry point.
- `ingestion.py` — `extract_text` dispatches on file extension (`.txt` decoded directly, `.pdf` via `pypdf`, wrapping `PdfReadError` into a domain `InvalidPdfError` rather than leaking the raw library exception). `ingest_document` is a documented deviation from the pure-module pattern (like `auth.py`'s session functions): it does real DB I/O directly — persists the `Document`, calls `chunking.split_into_chunks`, calls `embeddings.embed_texts` on the chunk contents, persists the `Chunk` rows with their embeddings attached, and flips `Document.status` from `pending` straight to `embedded` (chunking and embedding happen synchronously in one request, so there's no externally-visible "chunked but not yet embedded" intermediate state).
- `retrieval.py` — `retrieve_relevant_chunks(session, document_id, query_embedding, top_k)` does a real pgvector nearest-neighbor query (via `Chunk.embedding.cosine_distance(...)`, using the HNSW index), scoped to one document and excluding null embeddings, returning `RetrievedChunk` (chunk + similarity score, `1 - distance`) ordered by relevance. Another documented DB-I/O module, same rationale as `ingestion.py` — the ranking has to happen in SQL to use the index, not by pulling every chunk into Python.
- `main.py` — app instance, lifespan hook that seeds a demo user via `seed.py`, and `GET /health`.

Planned modules (Milestones 6-7, see `LEDGER.md` and the project plan for the full roadmap): `generation.py` (Anthropic Claude RAG calls), `confidence.py` (pure review-flag decision logic), `review.py` (review-flag persistence).

- `routers/documents.py` — `POST /documents` (upload, enforces a 10MB size limit before calling `ingestion.ingest_document`, translates its domain errors to 415/422), `GET /documents` (list, scoped to `current_user`), `GET /documents/{id}` (detail with chunks). All three require auth (`CurrentUser`). Documents are scoped per-owner: a document ID belonging to another user 404s (not 403), same anti-enumeration principle already established for auth in Milestone 2 — `get_owned_document` is the shared helper for that check, exported (not module-private) specifically so `routers/questions.py` can reuse it rather than duplicating the ownership check.
- `routers/questions.py` — `POST /documents/{id}/questions`: looks up the document via `get_owned_document` (404 for other users' documents), 422s if `Document.status != EMBEDDED` (defensive — every document reachable through the API today is always `embedded` by the time it's persisted, but this guards against a future async ingestion pipeline reintroducing a real gap), persists the `Question`, embeds the question text, calls `retrieval.retrieve_relevant_chunks`, and returns the ranked matches with scores. No answer generation yet — that's Milestone 6.

### Migrations

Schema changes go through Alembic (`alembic/versions/`), not app startup. `alembic/env.py` imports `compliance_doc_assistant.models` for autogenerate metadata and reads `COMPLIANCE_DATABASE_URL` the same way the app does.

## Frontend

Next.js (TypeScript, App Router) app in `frontend/`, kept as a fully separate package (own `package.json`/lockfile, no shared code with the backend) — a deliberate portfolio decision to diversify beyond evalops-dashboard's server-rendered Jinja2/zero-client-JS approach. As of Milestone 1, it's a placeholder landing page only.

## Roadmap

See `LEDGER.md` for shipped milestones and the project plan for what's next. Confirm with the user before starting a new milestone rather than assuming scope.
