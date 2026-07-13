FROM python:3.12-slim

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY pyproject.toml uv.lock* ./
RUN uv sync --no-install-project

COPY . .
RUN uv sync

# Bakes the sentence-transformers embedding model into the image at build
# time, so containers don't need Hub network access or a slow first-request
# download at runtime.
RUN PYTHONPATH=src uv run python -c \
    "from compliance_doc_assistant.embeddings import embed_texts; embed_texts(['warmup'])"

EXPOSE 8000

# $PORT is injected by Render (and similar PaaS hosts) at a value chosen at
# deploy time; falls back to 8000 for docker-compose/local use where nothing
# sets it. Migrations run here (not as a separate Render "pre-deploy" step)
# so the image is self-sufficient for any host that just runs the container.
CMD ["sh", "-c", "uv run alembic upgrade head && uv run uvicorn --app-dir src --host 0.0.0.0 --port ${PORT:-8000} compliance_doc_assistant.main:app"]
