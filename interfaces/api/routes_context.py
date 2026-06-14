from __future__ import annotations

from fastapi import APIRouter

from application.use_cases.inspect_context import inspect_context, inspect_trace


router = APIRouter()


@router.get("/projects/{project_id}/chapters/{chapter_id}/trace")
def api_get_trace(project_id: str, chapter_id: int) -> dict:
    return inspect_trace(project_id, chapter_id)


@router.get("/projects/{project_id}/chapters/{chapter_id}/context-audit")
def api_get_context_audit(project_id: str, chapter_id: int) -> dict:
    return inspect_context(project_id, chapter_id)
