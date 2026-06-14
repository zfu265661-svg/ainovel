from __future__ import annotations

from fastapi import FastAPI

from interfaces.api.routes_chapter import router as chapter_router
from interfaces.api.routes_context import router as context_router
from interfaces.api.routes_project import router as project_router
from interfaces.api.routes_reports import router as reports_router
from interfaces.api.routes_threads import router as threads_router


app = FastAPI(title="Novel Narrative Engine", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(project_router)
app.include_router(chapter_router)
app.include_router(context_router)
app.include_router(threads_router)
app.include_router(reports_router)
