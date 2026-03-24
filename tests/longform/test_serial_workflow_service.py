from __future__ import annotations

from pathlib import Path

from core.longform.project_state_repository import initialize_loop_state, save_project_loop_state
from core.longform.serial_workflow_service import (
    STATUS_ALREADY_COMPLETED,
    STATUS_COMPLETED,
    STATUS_FAILED,
    run_five_chapter_loop,
)
from core.project_service import create_project_structure


def test_run_five_chapter_loop_runs_from_chapter_one_through_five(
    monkeypatch,
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "serial-project"
    create_project_structure(
        str(project_root),
        title="Test Novel",
        topic="xianxia",
        style="cold",
        target="serial",
    )
    initialize_loop_state(str(project_root), target_chapter_count=5)

    called_chapters: list[int] = []

    def fake_run_single_chapter(project_root: str, chapter_no: int | None = None) -> dict[str, object]:
        assert chapter_no is not None
        called_chapters.append(chapter_no)
        return {
            "chapter_no": chapter_no,
            "status": "completed",
            "artifacts": {"draft_path": f"{project_root}/docs/ch{chapter_no:03d}.draft.md"},
            "suggestion_committed": True,
            "checkpoint_written": True,
            "error": None,
        }

    monkeypatch.setattr(
        "core.longform.serial_workflow_service.run_single_chapter",
        fake_run_single_chapter,
    )

    result = run_five_chapter_loop(str(project_root))

    assert called_chapters == [1, 2, 3, 4, 5]
    assert result["started_from"] == 1
    assert result["ended_at"] == 5
    assert result["completed_chapters"] == [1, 2, 3, 4, 5]
    assert result["failed_chapter"] is None
    assert result["status"] == STATUS_COMPLETED
    assert len(result["per_chapter_results"]) == 5


def test_run_five_chapter_loop_stops_immediately_when_one_chapter_fails(
    monkeypatch,
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "serial-project"
    create_project_structure(
        str(project_root),
        title="Test Novel",
        topic="xianxia",
        style="cold",
        target="serial",
    )
    initialize_loop_state(str(project_root), target_chapter_count=5)

    called_chapters: list[int] = []

    def fake_run_single_chapter(project_root: str, chapter_no: int | None = None) -> dict[str, object]:
        assert chapter_no is not None
        called_chapters.append(chapter_no)
        if chapter_no == 3:
            return {
                "chapter_no": 3,
                "status": "failed",
                "artifacts": {},
                "suggestion_committed": False,
                "checkpoint_written": True,
                "error": "chapter failed",
            }
        return {
            "chapter_no": chapter_no,
            "status": "completed",
            "artifacts": {},
            "suggestion_committed": True,
            "checkpoint_written": True,
            "error": None,
        }

    monkeypatch.setattr(
        "core.longform.serial_workflow_service.run_single_chapter",
        fake_run_single_chapter,
    )

    result = run_five_chapter_loop(str(project_root))

    assert called_chapters == [1, 2, 3]
    assert result["started_from"] == 1
    assert result["ended_at"] == 3
    assert result["completed_chapters"] == [1, 2]
    assert result["failed_chapter"] == 3
    assert result["status"] == STATUS_FAILED
    assert len(result["per_chapter_results"]) == 3


def test_run_five_chapter_loop_resumes_from_next_chapter_no(
    monkeypatch,
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "serial-project"
    create_project_structure(
        str(project_root),
        title="Test Novel",
        topic="xianxia",
        style="cold",
        target="serial",
    )
    initial_state = initialize_loop_state(str(project_root), target_chapter_count=5)
    save_project_loop_state(
        str(project_root),
        {
            **initial_state,
            "status": "ready",
            "last_completed_chapter_no": 2,
            "next_chapter_no": 3,
            "current_chapter_no": None,
        },
    )

    called_chapters: list[int] = []

    def fake_run_single_chapter(project_root: str, chapter_no: int | None = None) -> dict[str, object]:
        assert chapter_no is not None
        called_chapters.append(chapter_no)
        return {
            "chapter_no": chapter_no,
            "status": "completed",
            "artifacts": {},
            "suggestion_committed": True,
            "checkpoint_written": True,
            "error": None,
        }

    monkeypatch.setattr(
        "core.longform.serial_workflow_service.run_single_chapter",
        fake_run_single_chapter,
    )

    result = run_five_chapter_loop(str(project_root))

    assert called_chapters == [3, 4, 5]
    assert result["started_from"] == 3
    assert result["ended_at"] == 5
    assert result["completed_chapters"] == [3, 4, 5]
    assert result["failed_chapter"] is None
    assert result["status"] == STATUS_COMPLETED


def test_run_five_chapter_loop_is_noop_after_five_chapters_are_already_done(
    monkeypatch,
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "serial-project"
    create_project_structure(
        str(project_root),
        title="Test Novel",
        topic="xianxia",
        style="cold",
        target="serial",
    )
    initial_state = initialize_loop_state(str(project_root), target_chapter_count=5)
    save_project_loop_state(
        str(project_root),
        {
            **initial_state,
            "status": "completed",
            "last_completed_chapter_no": 5,
            "next_chapter_no": 6,
            "current_chapter_no": None,
        },
    )

    called = {"count": 0}

    def fake_run_single_chapter(project_root: str, chapter_no: int | None = None) -> dict[str, object]:
        called["count"] += 1
        return {
            "chapter_no": chapter_no or 0,
            "status": "completed",
            "artifacts": {},
            "suggestion_committed": True,
            "checkpoint_written": True,
            "error": None,
        }

    monkeypatch.setattr(
        "core.longform.serial_workflow_service.run_single_chapter",
        fake_run_single_chapter,
    )

    result = run_five_chapter_loop(str(project_root))

    assert called["count"] == 0
    assert result == {
        "started_from": 6,
        "ended_at": 5,
        "completed_chapters": [],
        "failed_chapter": None,
        "status": STATUS_ALREADY_COMPLETED,
        "per_chapter_results": [],
    }
