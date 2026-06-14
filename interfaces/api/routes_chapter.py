from __future__ import annotations

from pydantic import BaseModel
from fastapi import APIRouter

from application.use_cases.run_chapter import run_chapter


router = APIRouter()


class RunChapterRequest(BaseModel):
    dry_run: bool = False
    review_before_commit: bool = False


@router.post("/projects/{project_id}/chapters/{chapter_id}/run")
def api_run_chapter(project_id: str, chapter_id: int, payload: RunChapterRequest | None = None) -> dict:
    payload = payload or RunChapterRequest()
    return run_chapter(
        project_id,
        chapter_id,
        dry_run=payload.dry_run,
        review_before_commit=payload.review_before_commit,
    )
