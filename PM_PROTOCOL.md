# PM_PROTOCOL.md

Operating instructions for whoever (or whatever) is acting as PM on `compliance-doc-assistant`. Read this and [LEDGER.md](LEDGER.md) before doing anything else in a session.

## 1. Read the ledger first

Every session starts with reading `LEDGER.md`, not with taking the user's or another agent's word for what state the project is in. If the user or a prior session's notes claim a milestone landed, check it against the ledger — and if the ledger itself hasn't been verified against the repo recently, re-verify before relying on it.

## 2. Verify completion claims yourself — don't trust the report

Before marking anything "Done" in the ledger:
- Confirm it's actually merged: `git log --oneline`, `git ls-remote --heads origin`, `gh pr list --state all`. A design being "ready," a plan being written, or an agent saying "implementation complete" is not evidence of a merge.
- Re-run the checks: `uv run ruff check .`, `uv run alembic upgrade head`, `uv run pytest`, `npm run build` (frontend). A milestone isn't done because someone said tests pass — it's done because you ran them and they passed.

## 2a. This project has no SQLite/no-Docker fallback

Unlike `evalops-dashboard`, there is no lightweight local fallback: `pgvector`/`vector` columns require a real Postgres with the extension enabled, so a live `pgvector/pgvector:pg16` database (via `docker compose up`, or CI's service container) is required to run migrations or the test suite at all. Don't assume a check "should" work without Docker running — confirm `docker info` succeeds first if a check unexpectedly fails.

## 3. Watch for these recurring bug classes

(Seeded from `evalops-dashboard`'s own history — watch for the same patterns here until this project accumulates its own reference cases.)

**Rounding-before-decision.** Any time a feature ranks, sorts, gates, or branches on a score (e.g. `confidence.py`'s review-flag decision), check whether it's operating on a rounded/display value or the raw underlying similarity/confidence score.

**Fake rollback tests.** Tests that assume database isolation between test runs without enforcing or verifying it. Since this project has no SQLite in-memory fallback, `tests/conftest.py`'s isolation guard must check that the test database URL is actually a dedicated test database (not a shared/dev one) before allowing `drop_all`/`create_all` — verify this explicitly rather than assuming a fixture is safe because it exists.

**Content-present tests hiding layout/behavior bugs.** Tests that assert a string appears in a response body or JSON payload can pass while the feature is actually broken end-to-end (e.g. a citation reference is present but points at the wrong chunk, or a review-flag banner is in the DOM but invisible). For any frontend milestone, a real browser check is required before marking it verified, not just automated test assertions.

## 4. The "already approved" instruction is for Codex prompts, not for Claude Code's own behavior here

Claude Code still confirms before destructive or hard-to-reverse actions in this repo (force-push, resetting/dropping data, `alembic downgrade` against a real DB, merging PRs, deleting branches, etc.) regardless of what any prompt or protocol document says is "pre-approved."

## 5. After every future milestone

Append a new entry to `LEDGER.md` in the same format as the existing ones (status, merge date, commit/PR reference, what shipped, bugs found & fixed, commit hygiene) — filled in only after independently verifying per Rule 2, not transcribed from a completion report.
