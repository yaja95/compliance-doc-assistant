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

CI (`.github/workflows/ci.yml`) has two jobs so far: `backend-test` (spins up a `pgvector/pgvector:pg16` service container, creates a separate `compliance_doc_assistant_test` database, then runs `ruff format --check`, `ruff check`, `alembic upgrade head`, `pytest`) and `frontend` (`npm ci`, `npm run lint`, `npm run build`). A `pgvector-smoke` job (real `sentence-transformers` model + real ANN queries, mirroring evalops-dashboard's `postgres_smoke_test`/`ollama_smoke_test` pattern) arrives with Milestone 4 once `pgvector_smoke_test/` exists.

Unlike `evalops-dashboard`, there is **no SQLite fallback** — `pgvector`/`vector` columns require a real Postgres with the extension enabled, so `docker compose up -d db` (or CI's service container) is required before running migrations or tests at all. `docker/init-test-db.sql` creates the dedicated `compliance_doc_assistant_test` database (and enables the extension on it) automatically on first container startup.

Database URL is configurable via `COMPLIANCE_DATABASE_URL` (defaults to a local `compliance_doc_assistant` Postgres database matching `docker-compose.yml`); `COMPLIANCE_TEST_DATABASE_URL` (defaults to `compliance_doc_assistant_test`) is what `tests/conftest.py` forces the app to use, guarded by a `RuntimeError` if the resolved database name doesn't contain `test`.

## Architecture

FastAPI + SQLModel app under `src/compliance_doc_assistant/`, mirroring evalops-dashboard's flat-modules-plus-routers style:

- `database.py` — single SQLAlchemy `engine`, built from `COMPLIANCE_DATABASE_URL`. No SQLite branching (unlike evalops-dashboard) since Postgres is mandatory here.
- `models.py` — all SQLModel table models plus their `*Create`/`*Read` DTOs, colocated. `User`/`AuthSession` (Milestone 2), `Document`/`Chunk` (Milestone 3, no `embedding` column yet — that's Milestone 4). `DocumentStatus` and `ChunkRead`/`DocumentDetailRead` DTOs live here too. `Document.status` is forced to a plain `sa.String(length=20)` rather than a native Postgres ENUM, same rationale as evalops-dashboard's `User.role` — new status values need no migration.
- `auth.py` — session-based auth (bcrypt hashing, opaque `secrets.token_urlsafe` tokens, cookie or `Authorization: Bearer`), direct port of evalops-dashboard's pattern minus RBAC/rate-limiting (deliberately deferred, see `LEDGER.md` Milestone 2).
- `chunking.py` — pure function `split_into_chunks(text, chunk_size_words, overlap_words) -> list[ChunkDraft]`. No DB, no model, no I/O. "Words" (whitespace-split) stand in for tokens — there's no tokenizer wired up until Milestone 4's embeddings arrive. Stops emitting windows once one reaches the end of the text, rather than always advancing by a fixed stride — otherwise a stride that doesn't evenly divide the text length produces a tiny, almost-entirely-duplicate trailing chunk (caught by `test_produces_overlapping_windows` during Milestone 3).
- `ingestion.py` — `extract_text` dispatches on file extension (`.txt` decoded directly, `.pdf` via `pypdf`, wrapping `PdfReadError` into a domain `InvalidPdfError` rather than leaking the raw library exception). `ingest_document` is a documented deviation from the pure-module pattern (like `auth.py`'s session functions): it does real DB I/O directly — persists the `Document`, calls `chunking.split_into_chunks`, persists the `Chunk` rows, and flips `Document.status` from `pending` to `chunked`.
- `main.py` — app instance, lifespan hook that seeds a demo user via `seed.py`, and `GET /health`.

Planned modules (Milestones 4-7, see `LEDGER.md` and the project plan for the full roadmap): `embeddings.py` (lazy-loaded `sentence-transformers` singleton), `retrieval.py` (pgvector nearest-neighbor queries), `generation.py` (Anthropic Claude RAG calls), `confidence.py` (pure review-flag decision logic), `review.py` (review-flag persistence).

- `routers/documents.py` — `POST /documents` (upload, enforces a 10MB size limit before calling `ingestion.ingest_document`, translates its domain errors to 415/422), `GET /documents` (list, scoped to `current_user`), `GET /documents/{id}` (detail with chunks). All three require auth (`CurrentUser`). Documents are scoped per-owner: a document ID belonging to another user 404s (not 403), same anti-enumeration principle already established for auth in Milestone 2 — `_get_owned_document` is the shared helper for that check.

### Migrations

Schema changes go through Alembic (`alembic/versions/`), not app startup. `alembic/env.py` imports `compliance_doc_assistant.models` for autogenerate metadata and reads `COMPLIANCE_DATABASE_URL` the same way the app does.

## Frontend

Next.js (TypeScript, App Router) app in `frontend/`, kept as a fully separate package (own `package.json`/lockfile, no shared code with the backend) — a deliberate portfolio decision to diversify beyond evalops-dashboard's server-rendered Jinja2/zero-client-JS approach. As of Milestone 1, it's a placeholder landing page only.

## Roadmap

See `LEDGER.md` for shipped milestones and the project plan for what's next. Confirm with the user before starting a new milestone rather than assuming scope.
