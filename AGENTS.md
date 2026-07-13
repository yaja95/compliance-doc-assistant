# compliance-doc-assistant Guide

This is a portfolio project for Forward Deployed Engineer roles.

## Working Norms

- Keep the first version small, correct, and easy to extend.
- Prefer clear business-facing names over clever abstractions.
- Run `uv run ruff format .`, `uv run ruff check .`, and `uv run pytest` before finishing backend changes when dependencies are installed. Run `npm run lint` and `npm run build` in `frontend/` before finishing frontend changes.
- Preserve the `src/` layout and keep tests focused on behavior.

## Product Goal

Build a compliance-document review assistant: upload a policy/regulatory document, ask natural-language questions, get source-grounded answers with citations back to the originating sections, and flag low-confidence answers for human review instead of asserting them confidently.
