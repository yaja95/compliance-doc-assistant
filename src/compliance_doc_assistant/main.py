from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlmodel import Session

from compliance_doc_assistant.database import engine
from compliance_doc_assistant.routers.auth import me_router
from compliance_doc_assistant.routers.auth import router as auth_router
from compliance_doc_assistant.routers.documents import router as documents_router
from compliance_doc_assistant.routers.questions import router as questions_router
from compliance_doc_assistant.routers.review import router as review_router
from compliance_doc_assistant.seed import seed_database


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    with Session(engine) as session:
        seed_database(session)
    yield


app = FastAPI(title="compliance-doc-assistant", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(me_router)
app.include_router(documents_router)
app.include_router(questions_router)
app.include_router(review_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
