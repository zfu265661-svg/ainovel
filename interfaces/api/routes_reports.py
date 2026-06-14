from __future__ import annotations

from fastapi import APIRouter

from application.use_cases.inspect_checkpoints import inspect_checkpoints
from application.use_cases.inspect_context import inspect_report


router = APIRouter()


@router.get("/projects/{project_id}/chapters/{chapter_id}/consistency-report")
def api_get_consistency_report(project_id: str, chapter_id: int) -> dict:
    return inspect_report(project_id, chapter_id)


@router.get("/projects/{project_id}/checkpoints")
def api_get_checkpoints(project_id: str) -> list[dict]:
    return inspect_checkpoints(project_id)
