# LEDGER.md

Running record of what has actually shipped in `compliance-doc-assistant`, verified against `git log` / `gh pr list`, not against completion reports. See [PM_PROTOCOL.md](PM_PROTOCOL.md) for how this file is maintained.

Numbering below follows commit order on `main`.

## Milestone 1 — Initial scaffold
- **Status:** Done
- **Merged:** 2026-07-13, commit [`d7bf428`](https://github.com/yaja95/compliance-doc-assistant/commit/d7bf428c21311dcb988ac6a9f56fbabca987f2a8), direct to `main` (no PR — matches evalops-dashboard's Milestone 0 convention for the initial scaffold). Verified via `git log`/`git ls-remote` against `origin/main` directly.
- **Post-merge checks re-run against `main`:** `ruff format --check .`, `ruff check .` clean; `alembic upgrade head` applies cleanly against a fresh `pgvector/pgvector:pg16` container; `pytest` 1/1 passing; `docker compose up -d --build` brings up `db` + `backend` with a live `GET /health` → `200 {"status":"ok"}`; `npm run lint` and `npm run build` clean in `frontend/`. CI run [`29214727972`](https://github.com/yaja95/compliance-doc-assistant/actions/runs/29214727972) — both `backend-test` and `frontend` jobs passed (1m27s).
- **Shipped:** FastAPI + SQLModel + Alembic backend skeleton (`src/compliance_doc_assistant/`) with a `GET /health` endpoint; Postgres+pgvector-only local dev via `docker-compose.yml` (no SQLite fallback, unlike evalops-dashboard — `pgvector` requires a real Postgres extension); `docker/init-test-db.sql` auto-creates a dedicated `compliance_doc_assistant_test` database with the extension enabled, so `tests/conftest.py`'s isolation guard (checks `test` appears in the resolved database name) has something real to point at; a placeholder Next.js (TypeScript, App Router) frontend in `frontend/`, kept as a fully separate package with no shared code with the backend; GitHub Actions CI (`backend-test` + `frontend` jobs — a `pgvector-smoke` job arrives with Milestone 4 once `pgvector_smoke_test/` exists); portfolio process docs (`AGENTS.md`, `PM_PROTOCOL.md`, `LEDGER.md`, `CLAUDE.md`, `README.md`) mirroring evalops-dashboard's format, with a new `PM_PROTOCOL.md` §2a documenting the no-SQLite-fallback divergence explicitly.
- **Commit hygiene:** No AI trailers, author is `Ajay Williams` only.
