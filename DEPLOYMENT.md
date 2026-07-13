# Deployment

This project deploys as two pieces: the backend (FastAPI + Postgres/pgvector) on Render, and the frontend (Next.js) on Vercel. There is no Render integration available to Claude Code in this environment, so the backend deploy is a set of manual dashboard steps for you to run — this doc is the exact recipe. The frontend can be deployed directly by Claude Code via its Vercel connection once the backend URL is known.

## Why two hosts

- **Render** runs long-lived Docker containers and managed Postgres with the `pgvector` extension — a good fit for this app's stateful backend (real Postgres, Alembic migrations, a baked-in `sentence-transformers` model).
- **Vercel** is the natural host for a Next.js frontend and is already connected in this environment.

## Cost note (read before clicking anything)

`render.yaml` requests a **`standard`** plan for the web service and **`basic-256mb`** for the database — these are **paid** plans, not Render's free tier. The backend loads `sentence-transformers`/`torch` into memory, which is likely to exceed the free tier's RAM. Check Render's current pricing before provisioning, and downgrade the plan in `render.yaml` (or the dashboard) if you'd rather start smaller and see if it's enough — Claude Code did not verify actual memory usage against a real Render instance.

## Step 1 — Confirm pgvector works on Render's managed Postgres

Not verified in this session (no Render access). Before setting up the full blueprint:
1. Create a small Postgres instance on Render (or use the one from Step 2 below).
2. Connect via `psql` (Render's dashboard gives you a connection command) and run:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
3. If that fails, stop and report back — the backend cannot run without it, and we'd need to reconsider (a different managed Postgres provider, or self-hosting Postgres on a Render private service using the same `pgvector/pgvector:pg16` image this project already uses locally).

## Step 2 — Deploy the backend

**Option A — Blueprint (recommended, uses `render.yaml`):**
1. In the Render dashboard: **New +** → **Blueprint**, point it at this repo (`yaja95/compliance-doc-assistant`), branch `main`.
2. Render reads `render.yaml` and proposes a database (`compliance-doc-assistant-db`) and a web service (`compliance-doc-assistant-backend`). Review the plans (see cost note above) and confirm.
3. Render provisions both and links `COMPLIANCE_DATABASE_URL` to the database automatically (via the blueprint's `fromDatabase` reference).

**Option B — Manual (if you'd rather not use the blueprint):**
1. **New +** → **PostgreSQL** → name it, pick a plan, create it. Note the **Internal Connection String**.
2. **New +** → **Web Service** → connect this repo → **Runtime: Docker** (Render will detect the `Dockerfile`) → pick a plan.
3. Set environment variables on the web service (Step 3 below).

## Step 3 — Environment variables on the backend service

Two are marked `sync: false` in `render.yaml`, meaning Render won't auto-fill them — set these yourself in the dashboard:

| Variable | Value |
|---|---|
| `ANTHROPIC_API_KEY` | Your Anthropic API key. Only you should ever enter this — Claude Code never sees it. |
| `FRONTEND_ORIGINS` | The Vercel deployment URL from Step 4 below (e.g. `https://compliance-doc-assistant.vercel.app`). Without this, the browser will block the frontend's API calls with a CORS error. |

If you went with Option B (manual), also set `COMPLIANCE_DATABASE_URL` to the Postgres instance's **Internal Connection String** — Render hands this out as `postgres://...` or `postgresql://...` (no driver in the scheme); the app normalizes this automatically (see `database.py`), so you don't need to edit the string.

`GENERATION_PROVIDER` defaults to `anthropic` in `render.yaml`. Ollama isn't practical to run on a lightweight Render web service (needs its own model server and meaningfully more RAM/CPU) — if you want it in production anyway, that's a separate, bigger infrastructure decision to make deliberately, not a quick env var flip.

## Step 4 — Deploy the frontend (Vercel, via Claude Code)

Once the backend is live and you have its Render URL (e.g. `https://compliance-doc-assistant-backend.onrender.com`):
1. Tell Claude Code the URL.
2. Claude Code bakes it into `frontend/.env.production` as `NEXT_PUBLIC_API_BASE_URL` and deploys via its Vercel connection (there's no Vercel tool for setting project environment variables directly in this environment, so the value is committed to a checked-in env file instead — redeploying is how it gets updated if the backend URL ever changes).
3. You'll get back a `*.vercel.app` URL — set that as `FRONTEND_ORIGINS` on the Render backend (Step 3) if you haven't already, so CORS allows it.

## Step 5 — Verify

- Visit the Vercel URL, log in with the seeded `demo` account (or set `SEED_USER_PASSWORD` on Render before first boot to change it from the dev-only default).
- Upload a document, ask a question, confirm citations and (if you trigger one) a review-flag banner render correctly.
- Check Render's logs for the backend if anything 500s — most likely causes are a missing `ANTHROPIC_API_KEY` (503 from `generation.py`, by design) or `FRONTEND_ORIGINS` not matching the Vercel URL exactly (CORS block, visible in the browser console, not the backend logs).
