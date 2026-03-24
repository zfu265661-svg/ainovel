from __future__ import annotations

from typing import Any

from core.longform.chapter_runner_service import (
    STATUS_COMPLETED as CHAPTER_STATUS_COMPLETED,
    run_single_chapter,
)
from core.longform.loop_state_service import get_resume_chapter_no
from core.longform.project_state_repository import load_project_loop_state


FINAL_CHAPTER_NO = 5
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_ALREADY_COMPLETED = "already_completed"


def run_five_chapter_loop(project_root: str) -> dict[str, Any]:
    """Run the minimum longform workflow from current resume point through chapter 5."""
    loop_state = load_project_loop_state(project_root)
    started_from = get_resume_chapter_no(loop_state)

    if started_from > FINAL_CHAPTER_NO:
        return {
            "started_from": started_from,
            "ended_at": FINAL_CHAPTER_NO,
            "completed_chapters": [],
            "failed_chapter": None,
            "status": STATUS_ALREADY_COMPLETED,
            "per_chapter_results": [],
        }

    completed_chapters: list[int] = []
    per_chapter_results: list[dict[str, Any]] = []

    for chapter_no in range(started_from, FINAL_CHAPTER_NO + 1):
        chapter_result = run_single_chapter(project_root, chapter_no=chapter_no)
        per_chapter_results.append(chapter_result)

        if chapter_result["status"] != CHAPTER_STATUS_COMPLETED:
            return {
                "started_from": started_from,
                "ended_at": chapter_no,
                "completed_chapters": completed_chapters,
                "failed_chapter": chapter_no,
                "status": STATUS_FAILED,
                "per_chapter_results": per_chapter_results,
            }

        completed_chapters.append(chapter_no)

    return {
        "started_from": started_from,
        "ended_at": FINAL_CHAPTER_NO,
        "completed_chapters": completed_chapters,
        "failed_chapter": None,
        "status": STATUS_COMPLETED,
        "per_chapter_results": per_chapter_results,
    }
