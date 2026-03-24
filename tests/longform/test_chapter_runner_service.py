from __future__ import annotations

from pathlib import Path

from core.longform.chapter_runner_service import (
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_REJECTED,
    run_single_chapter,
)
from core.longform.project_state_repository import (
    get_chapter_checkpoint_path,
    initialize_loop_state,
    load_project_loop_state,
)
from core.project_service import create_project_structure
from core.storage import load_json


def test_run_single_chapter_successfully_commits_and_advances_loop_state(
    monkeypatch,
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "runner-project"
    create_project_structure(
        str(project_root),
        title="Test Novel",
        topic="xianxia",
        style="cold",
        target="serial",
    )
    initialize_loop_state(str(project_root), target_chapter_count=5)

    monkeypatch.setattr(
        "core.longform.chapter_runner_service.write_chapter",
        lambda project_root, chapter_no: {
            "chapter_no": chapter_no,
            "draft_path": f"{project_root}/docs/ch{chapter_no:03d}.draft.md",
            "rewrite_path": f"{project_root}/docs/ch{chapter_no:03d}.rewrite.md",
            "summary_path": f"{project_root}/docs/ch{chapter_no:03d}.summary.md",
            "suggestion_path": f"{project_root}/suggestions/ch{chapter_no:03d}.suggestion.json",
        },
    )
    monkeypatch.setattr(
        "core.longform.chapter_runner_service.commit_suggestion",
        lambda project_root, chapter_no: {
            "chapter_no": chapter_no,
        },
    )

    result = run_single_chapter(str(project_root))

    assert result == {
        "chapter_no": 1,
        "status": STATUS_COMPLETED,
        "artifacts": {
            "draft_path": f"{project_root}/docs/ch001.draft.md",
            "rewrite_path": f"{project_root}/docs/ch001.rewrite.md",
            "summary_path": f"{project_root}/docs/ch001.summary.md",
            "suggestion_path": f"{project_root}/suggestions/ch001.suggestion.json",
        },
        "suggestion_committed": True,
        "checkpoint_written": True,
        "error": None,
    }

    loop_state = load_project_loop_state(str(project_root))
    assert loop_state["status"] == "ready"
    assert loop_state["last_completed_chapter_no"] == 1
    assert loop_state["next_chapter_no"] == 2
    checkpoint = load_json(get_chapter_checkpoint_path(str(project_root), 1))
    assert checkpoint["status"] == STATUS_COMPLETED
    assert checkpoint["suggestion_committed"] is True
    assert checkpoint["loop_state"]["next_chapter_no"] == 2


def test_run_single_chapter_keeps_resume_pointer_when_write_fails(
    monkeypatch,
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "runner-project"
    create_project_structure(
        str(project_root),
        title="Test Novel",
        topic="xianxia",
        style="cold",
        target="serial",
    )
    initialize_loop_state(str(project_root), target_chapter_count=5)

    monkeypatch.setattr(
        "core.longform.chapter_runner_service.write_chapter",
        lambda project_root, chapter_no: (_ for _ in ()).throw(RuntimeError("draft failed")),
    )

    result = run_single_chapter(str(project_root))

    assert result == {
        "chapter_no": 1,
        "status": STATUS_FAILED,
        "artifacts": {},
        "suggestion_committed": False,
        "checkpoint_written": True,
        "error": "draft failed",
    }

    loop_state = load_project_loop_state(str(project_root))
    assert loop_state["status"] == "failed"
    assert loop_state["current_chapter_no"] == 1
    assert loop_state["next_chapter_no"] == 1
    checkpoint = load_json(get_chapter_checkpoint_path(str(project_root), 1))
    assert checkpoint["status"] == STATUS_FAILED
    assert checkpoint["suggestion_committed"] is False
    assert checkpoint["loop_state"]["next_chapter_no"] == 1


def test_run_single_chapter_keeps_resume_pointer_when_commit_fails(
    monkeypatch,
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "runner-project"
    create_project_structure(
        str(project_root),
        title="Test Novel",
        topic="xianxia",
        style="cold",
        target="serial",
    )
    initialize_loop_state(str(project_root), target_chapter_count=5)

    monkeypatch.setattr(
        "core.longform.chapter_runner_service.write_chapter",
        lambda project_root, chapter_no: {
            "chapter_no": chapter_no,
            "draft_path": f"{project_root}/docs/ch{chapter_no:03d}.draft.md",
            "rewrite_path": f"{project_root}/docs/ch{chapter_no:03d}.rewrite.md",
            "summary_path": f"{project_root}/docs/ch{chapter_no:03d}.summary.md",
            "suggestion_path": f"{project_root}/suggestions/ch{chapter_no:03d}.suggestion.json",
        },
    )
    monkeypatch.setattr(
        "core.longform.chapter_runner_service.commit_suggestion",
        lambda project_root, chapter_no: (_ for _ in ()).throw(RuntimeError("commit failed")),
    )

    result = run_single_chapter(str(project_root))

    assert result == {
        "chapter_no": 1,
        "status": STATUS_FAILED,
        "artifacts": {
            "draft_path": f"{project_root}/docs/ch001.draft.md",
            "rewrite_path": f"{project_root}/docs/ch001.rewrite.md",
            "summary_path": f"{project_root}/docs/ch001.summary.md",
            "suggestion_path": f"{project_root}/suggestions/ch001.suggestion.json",
        },
        "suggestion_committed": False,
        "checkpoint_written": True,
        "error": "commit failed",
    }

    loop_state = load_project_loop_state(str(project_root))
    assert loop_state["status"] == "failed"
    assert loop_state["current_chapter_no"] == 1
    assert loop_state["next_chapter_no"] == 1
    checkpoint = load_json(get_chapter_checkpoint_path(str(project_root), 1))
    assert checkpoint["status"] == STATUS_FAILED
    assert checkpoint["artifacts"]["draft_path"].endswith("ch001.draft.md")


def test_run_single_chapter_uses_updated_resume_pointer_on_repeat_runs(
    monkeypatch,
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "runner-project"
    create_project_structure(
        str(project_root),
        title="Test Novel",
        topic="xianxia",
        style="cold",
        target="serial",
    )
    initialize_loop_state(str(project_root), target_chapter_count=5)

    called_chapters: list[int] = []

    def fake_write_chapter(project_root: str, chapter_no: int) -> dict[str, object]:
        called_chapters.append(chapter_no)
        return {
            "chapter_no": chapter_no,
            "draft_path": f"{project_root}/docs/ch{chapter_no:03d}.draft.md",
            "rewrite_path": f"{project_root}/docs/ch{chapter_no:03d}.rewrite.md",
            "summary_path": f"{project_root}/docs/ch{chapter_no:03d}.summary.md",
            "suggestion_path": f"{project_root}/suggestions/ch{chapter_no:03d}.suggestion.json",
        }

    monkeypatch.setattr(
        "core.longform.chapter_runner_service.write_chapter",
        fake_write_chapter,
    )
    monkeypatch.setattr(
        "core.longform.chapter_runner_service.commit_suggestion",
        lambda project_root, chapter_no: {"chapter_no": chapter_no},
    )

    first_result = run_single_chapter(str(project_root))
    second_result = run_single_chapter(str(project_root))
    rejected_result = run_single_chapter(str(project_root), chapter_no=1)

    assert called_chapters == [1, 2]
    assert first_result["chapter_no"] == 1
    assert second_result["chapter_no"] == 2
    assert rejected_result["status"] == STATUS_REJECTED
    assert rejected_result["suggestion_committed"] is False
    loop_state = load_project_loop_state(str(project_root))
    assert loop_state["next_chapter_no"] == 3
