from __future__ import annotations

from pathlib import Path
from typing import Any

from core.longform.loop_state_service import (
    get_resume_chapter_no,
    mark_chapter_completed,
    mark_chapter_failed,
    mark_chapter_started,
)
from core.longform.project_state_repository import (
    get_chapter_checkpoint_path,
    get_chapter_review_path,
    get_chapter_snapshot_path,
    load_project_loop_state,
    save_project_loop_state,
)
from core.longform.status_service import derive_failure_stage
from core.storage import save_json
from core.workflow_service import commit_suggestion, write_chapter


STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_REJECTED = "rejected"


def run_single_chapter(project_root: str, chapter_no: int | None = None) -> dict[str, Any]:
    """Run one resumable chapter step on top of the existing Phase 1 workflow."""
    initial_state = load_project_loop_state(project_root)
    target_chapter_no = (
        get_resume_chapter_no(initial_state)
        if chapter_no is None
        else chapter_no
    )
    write_result: dict[str, Any] | None = None

    try:
        running_state = mark_chapter_started(initial_state, target_chapter_no)
    except ValueError as exc:
        return _build_result(
            chapter_no=target_chapter_no,
            status=STATUS_REJECTED,
            write_result=None,
            review_path=None,
            snapshot_path=None,
            suggestion_committed=False,
            checkpoint_written=False,
            failure_stage=None,
            error=str(exc),
        )

    save_project_loop_state(project_root, running_state)

    try:
        write_result = write_chapter(project_root, target_chapter_no)
        commit_suggestion(project_root, target_chapter_no)

        completed_state = mark_chapter_completed(running_state, target_chapter_no)
        save_project_loop_state(project_root, completed_state)

        result = _build_result(
            chapter_no=target_chapter_no,
            status=STATUS_COMPLETED,
            write_result=write_result,
            review_path=_get_existing_review_path(project_root, target_chapter_no),
            snapshot_path=_get_existing_snapshot_path(project_root, target_chapter_no),
            suggestion_committed=True,
            checkpoint_written=False,
            failure_stage=None,
        )
        checkpoint_written = _write_checkpoint(
            project_root=project_root,
            result=result,
            loop_state=completed_state,
        )
        return {
            **result,
            "checkpoint_written": checkpoint_written,
        }
    except Exception as exc:
        failed_state = mark_chapter_failed(running_state, target_chapter_no)
        save_project_loop_state(project_root, failed_state)

        result = _build_result(
            chapter_no=target_chapter_no,
            status=STATUS_FAILED,
            write_result=write_result,
            review_path=_get_existing_review_path(project_root, target_chapter_no),
            snapshot_path=_get_existing_snapshot_path(project_root, target_chapter_no),
            suggestion_committed=False,
            checkpoint_written=False,
            failure_stage=_derive_failure_stage(write_result, str(exc)),
            error=str(exc),
        )
        checkpoint_written = _write_checkpoint(
            project_root=project_root,
            result=result,
            loop_state=failed_state,
        )
        return {
            **result,
            "checkpoint_written": checkpoint_written,
        }


def _write_checkpoint(
    project_root: str,
    result: dict[str, Any],
    loop_state: dict[str, Any],
) -> bool:
    checkpoint_path = get_chapter_checkpoint_path(project_root, result["chapter_no"])
    checkpoint_payload = {
        "chapter_no": result["chapter_no"],
        "status": result["status"],
        "failure_stage": result["failure_stage"],
        "artifacts": result["artifacts"],
        "suggestion_committed": result["suggestion_committed"],
        "error": result["error"],
        "loop_state": {
            "status": loop_state["status"],
            "next_chapter_no": loop_state["next_chapter_no"],
            "last_completed_chapter_no": loop_state["last_completed_chapter_no"],
            "current_chapter_no": loop_state["current_chapter_no"],
        },
    }
    save_json(checkpoint_path, checkpoint_payload)
    return True


def _build_result(
    chapter_no: int,
    status: str,
    write_result: dict[str, Any] | None,
    review_path: str | None,
    snapshot_path: str | None,
    suggestion_committed: bool,
    checkpoint_written: bool,
    failure_stage: str | None,
    error: str | None = None,
) -> dict[str, Any]:
    artifacts = {}
    if isinstance(write_result, dict):
        artifacts = {
            "draft_path": write_result.get("draft_path"),
            "rewrite_path": write_result.get("rewrite_path"),
            "summary_path": write_result.get("summary_path"),
            "suggestion_path": write_result.get("suggestion_path"),
        }
        if review_path is not None:
            artifacts["review_path"] = review_path
        if snapshot_path is not None:
            artifacts["snapshot_path"] = snapshot_path

    return {
        "chapter_no": chapter_no,
        "status": status,
        "artifacts": artifacts,
        "suggestion_committed": suggestion_committed,
        "checkpoint_written": checkpoint_written,
        "failure_stage": failure_stage,
        "error": error,
    }


def _derive_failure_stage(
    write_result: dict[str, Any] | None,
    error_message: str,
) -> str:
    if write_result is None:
        return "write_chapter"
    return derive_failure_stage(error_message, default_stage="unknown") or "unknown"


def _get_existing_review_path(project_root: str, chapter_no: int) -> str | None:
    review_path = get_chapter_review_path(project_root, chapter_no)
    if Path(review_path).is_file():
        return review_path
    return None


def _get_existing_snapshot_path(project_root: str, chapter_no: int) -> str | None:
    snapshot_path = get_chapter_snapshot_path(project_root, chapter_no)
    if Path(snapshot_path).is_file():
        return snapshot_path
    return None
