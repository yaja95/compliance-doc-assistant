from fastapi import FastAPI

app = FastAPI(title="compliance-doc-assistant")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
