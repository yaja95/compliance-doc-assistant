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

CMD ["uv", "run", "uvicorn", "--app-dir", "src", "--host", "0.0.0.0", "compliance_doc_assistant.main:app"]
