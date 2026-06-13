from __future__ import annotations

from pathlib import Path

import pytest

import phase2_cli
from core.longform.project_state_repository import initialize_loop_state
from core.storage import save_json


def test_init_loop_command_runs_successfully(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(
        phase2_cli,
        "initialize_loop_state",
        lambda project_root, target_chapter_count: {
            "start_chapter_no": 1,
            "target_chapter_count": target_chapter_count,
            "next_chapter_no": 1,
        },
    )

    exit_code = phase2_cli.main(["init-loop", "--root", "D:/tmp/novel"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "D:/tmp/novel" in output
    assert "5" in output


def test_show_status_command_prints_status_report(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(
        phase2_cli,
        "build_project_status_report",
        lambda project_root: {
            "workflow_status": "ready",
            "start_chapter_no": 1,
            "target_chapter_count": 5,
            "current_chapter_no": None,
            "next_chapter_no": 3,
            "loop_state_last_completed_chapter_no": 2,
            "last_successfully_committed_chapter_no": 2,
            "last_successfully_committed_source": "artifact_scan",
            "commit_scan_status": "exact",
            "commit_loop_drift": False,
            "commit_loop_drift_explanation": "loop_state and committed artifact markers agree.",
            "manual_commit_note": None,
            "last_attempted_chapter_no": 3,
            "last_attempt_status": "ready",
            "last_failure_stage": None,
            "last_error": None,
            "formal_state_health": "missing_optional",
            "formal_state_missing_files": ["story_bible.json"],
            "formal_state_required_missing_files": [],
            "formal_state_corrupt_files": [],
            "formal_state_corrupt_file_errors": {},
            "narrative_state_machine": {
                "formal_state": {
                    "targets": ["characters", "timeline", "foreshadow"],
                    "health": "missing_optional",
                },
                "commit_boundary": {"enhanced_state_committed": False},
            },
            "can_continue": True,
            "next_action": "continue_from_chapter:3",
            "unresolved_snapshot_exists": False,
            "unresolved_snapshot_chapters": [],
            "stale_snapshot_exists": False,
            "stale_snapshot_chapters": [],
            "artifact_focus_chapter_no": 3,
            "artifact_relation_status": "partial",
            "artifact_relation_explanation": "some chapter artifacts are absent.",
            "checkpoint_path": "D:/tmp/novel/checkpoints/ch003.checkpoint.json",
            "review_path": "D:/tmp/novel/reviews/ch003.review.json",
            "suggestion_path": "D:/tmp/novel/suggestions/ch003.suggestion.json",
            "snapshot_path": "D:/tmp/novel/snapshots/ch003.snapshot.json",
        },
    )

    exit_code = phase2_cli.main(["show-status", "--root", "D:/tmp/novel"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "workflow_status: ready" in output
    assert "next_chapter_no: 3" in output
    assert "last_successfully_committed_chapter_no: 2" in output
    assert "formal_state_health: missing_optional" in output
    assert "formal_state_missing_files: [story_bible.json]" in output
    assert "formal_state_corrupt_file_errors: {}" in output
    assert "narrative_state_machine:" in output
    assert "can_continue: True" in output
    assert "next_action: continue_from_chapter:3" in output
    assert "commit_loop_drift_explanation:" in output
    assert "manual_commit_note: None" in output
    assert "artifact_relation_status: partial" in output
    assert "artifact_relation_explanation:" in output
    assert "review_path: D:/tmp/novel/reviews/ch003.review.json" in output
    assert len(output.splitlines()) <= 40


def test_show_status_command_supports_legacy_project_without_phase3_state(
    tmp_path: Path,
    capsys,
) -> None:
    project_root = tmp_path / "legacy-cli-project"
    project_root.mkdir()
    save_json(
        str(project_root / "project.json"),
        {
            "project_id": "legacy-cli-project",
            "title": "Legacy CLI Novel",
            "topic": "xianxia",
            "style": "cold",
            "target": "serial",
            "current_chapter_no": 1,
            "status": "created",
        },
    )
    save_json(str(project_root / "chapters.json"), {"chapters": []})
    save_json(str(project_root / "characters.json"), {"characters": []})
    save_json(str(project_root / "timeline.json"), {"events": []})
    save_json(str(project_root / "foreshadow.json"), {"items": []})
    initialize_loop_state(str(project_root), target_chapter_count=5)

    exit_code = phase2_cli.main(["show-status", "--root", str(project_root)])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "formal_state_health: missing_optional" in output
    assert "can_continue: True" in output
    assert "story_bible.json" in output


def test_inspect_context_command_prints_report(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(
        phase2_cli,
        "build_context_inspection_report",
        lambda project_root, chapter_no: {
            "chapter_no": chapter_no,
            "chapter": {"chapter_no": chapter_no, "title": "Chapter Three"},
            "selected_context_counts": {"characters": 1, "locations": 1},
            "selected_context_labels": {"characters": ["Lin Yue"], "locations": ["North Gate"]},
            "context_audit": {"chapter_no": chapter_no, "selected": {"locations": []}},
            "summary_chain": {"previous_summary": {"selected": True}},
            "sources": {"outline_path": "D:/tmp/novel/docs/outline.md"},
            "selected_context": {"characters": [{"name": "Lin Yue"}]},
        },
    )

    exit_code = phase2_cli.main(
        ["inspect-context", "--root", "D:/tmp/novel", "--chapter", "3"]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Context inspection" in output
    assert "chapter_no: 3" in output
    assert "selected_context_counts:" in output
    assert "context_audit:" in output


def test_inspect_story_bible_command_prints_report(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(
        phase2_cli,
        "build_story_bible_inspection_report",
        lambda project_root: {
            "enhanced_state_health": "missing_optional",
            "missing_optional_files": ["story_bible.json"],
            "corrupt_optional_files": [],
            "corrupt_file_errors": {},
            "counts": {"plot_threads": 0},
            "files": {},
        },
    )

    exit_code = phase2_cli.main(["inspect-story-bible", "--root", "D:/tmp/novel"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Story Bible inspection" in output
    assert "enhanced_state_health: missing_optional" in output
    assert "missing_optional_files: [story_bible.json]" in output


def test_inspect_plot_threads_command_prints_report(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(
        phase2_cli,
        "build_plot_threads_inspection_report",
        lambda project_root: {
            "path": "D:/tmp/novel/plot_threads.json",
            "health": "healthy",
            "missing_optional_files": [],
            "corrupt_optional_files": [],
            "corrupt_file_errors": {},
            "total": 2,
            "status_counts": {"active": 1, "resolved": 1},
            "type_counts": {"main": 1, "subplot": 1},
            "graph": {"graph_fields_present": False},
        },
    )

    exit_code = phase2_cli.main(["inspect-plot-threads", "--root", "D:/tmp/novel"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Plot threads inspection" in output
    assert "health: healthy" in output
    assert "total: 2" in output


def test_inspect_story_bible_command_supports_legacy_project_without_phase3_state(
    tmp_path: Path,
    capsys,
) -> None:
    project_root = tmp_path / "legacy-inspect-cli-project"
    project_root.mkdir()
    save_json(
        str(project_root / "project.json"),
        {
            "project_id": "legacy-inspect-cli-project",
            "title": "Legacy CLI Novel",
            "topic": "xianxia",
            "style": "cold",
            "target": "serial",
            "current_chapter_no": 1,
            "status": "created",
        },
    )
    save_json(str(project_root / "chapters.json"), {"chapters": []})
    save_json(str(project_root / "characters.json"), {"characters": []})
    save_json(str(project_root / "timeline.json"), {"events": []})
    save_json(str(project_root / "foreshadow.json"), {"items": []})

    exit_code = phase2_cli.main(["inspect-story-bible", "--root", str(project_root)])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "enhanced_state_health: missing_optional" in output
    assert "story_bible.json" in output


def test_prepare_review_command_prints_review_report(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(
        phase2_cli,
        "prepare_review",
        lambda project_root, chapter_no: _review_cli_payload(chapter_no, "pending"),
    )

    exit_code = phase2_cli.main(
        ["prepare-review", "--root", "D:/tmp/novel", "--chapter", "1"]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Review prepared" in output
    assert "status: pending" in output
    assert "approved_suggestion_summary:" in output


def test_list_reviews_command_prints_reviews(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(
        phase2_cli,
        "list_reviews",
        lambda project_root: [
            {
                "chapter_no": 1,
                "status": "pending",
                "has_consistency_check": True,
                "committed": False,
                "review_path": "D:/tmp/novel/reviews/ch001.review.json",
            }
        ],
    )

    exit_code = phase2_cli.main(["list-reviews", "--root", "D:/tmp/novel"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Review list" in output
    assert "pending" in output
    assert "ch001.review.json" in output


def test_show_review_command_prints_review_detail(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(
        phase2_cli,
        "load_review_for_display",
        lambda project_root, chapter_no: _review_cli_payload(chapter_no, "approved"),
    )

    exit_code = phase2_cli.main(
        ["show-review", "--root", "D:/tmp/novel", "--chapter", "1"]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Review detail" in output
    assert "status: approved" in output
    assert "review_path: D:/tmp/novel/reviews/ch001.review.json" in output


def test_approve_review_command_prints_review_report(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(
        phase2_cli,
        "approve_review",
        lambda project_root, chapter_no: _review_cli_payload(chapter_no, "approved"),
    )

    exit_code = phase2_cli.main(
        ["approve-review", "--root", "D:/tmp/novel", "--chapter", "1"]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Review approved" in output
    assert "status: approved" in output


def test_reject_review_command_prints_review_report(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(
        phase2_cli,
        "reject_review",
        lambda project_root, chapter_no, reason: {
            **_review_cli_payload(chapter_no, "rejected"),
            "reject_reason": reason,
        },
    )

    exit_code = phase2_cli.main(
        [
            "reject-review",
            "--root",
            "D:/tmp/novel",
            "--chapter",
            "1",
            "--reason",
            "not ready",
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Review rejected" in output
    assert "status: rejected" in output
    assert "reject_reason: not ready" in output


def test_commit_approved_command_prints_commit_result(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(
        phase2_cli,
        "commit_approved_review",
        lambda project_root, chapter_no: {
            "chapter_no": chapter_no,
            "suggestion_path": "D:/tmp/novel/suggestions/ch001.suggestion.json",
            "characters_updated": 1,
            "timeline_updated": 0,
            "foreshadow_updated": 0,
        },
    )
    monkeypatch.setattr(
        phase2_cli,
        "build_chapter_diagnostic_report",
        lambda project_root, chapter_no: {
            "review_path": "D:/tmp/novel/reviews/ch001.review.json",
            "snapshot_path": "D:/tmp/novel/snapshots/ch001.snapshot.json",
            "artifact_relation_status": "partial",
        },
    )

    exit_code = phase2_cli.main(
        ["commit-approved", "--root", "D:/tmp/novel", "--chapter", "1"]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Approved review committed" in output
    assert "characters_updated: 1" in output
    assert "review_path: D:/tmp/novel/reviews/ch001.review.json" in output


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("Review for chapter 1 was not found.", "was not found"),
        ("Review for chapter 1 has not been approved.", "has not been approved"),
        ("Review for chapter 1 has been rejected.", "has been rejected"),
        ("Review for chapter 1 has already been committed.", "already been committed"),
    ],
)
def test_commit_approved_command_prints_clear_gate_errors(
    monkeypatch,
    capsys,
    message: str,
    expected: str,
) -> None:
    monkeypatch.setattr(
        phase2_cli,
        "commit_approved_review",
        lambda project_root, chapter_no: (_ for _ in ()).throw(ValueError(message)),
    )

    exit_code = phase2_cli.main(
        ["commit-approved", "--root", "D:/tmp/novel", "--chapter", "1"]
    )

    output = capsys.readouterr().out
    assert exit_code == 1
    assert expected in output


def test_run_five_command_calls_longform_workflow(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(
        phase2_cli,
        "run_five_chapter_loop",
        lambda project_root: {
            "started_from": 1,
            "ended_at": 5,
            "completed_chapters": [1, 2, 3, 4, 5],
            "failed_chapter": None,
            "status": "completed",
            "per_chapter_results": [],
        },
    )

    exit_code = phase2_cli.main(["run-five", "--root", "D:/tmp/novel"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "started_from: 1" in output
    assert "ended_at: 5" in output
    assert "status: completed" in output
    assert "completed_count: 5" in output


def test_run_five_command_prints_failed_result_clearly(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(
        phase2_cli,
        "run_five_chapter_loop",
        lambda project_root: {
            "started_from": 2,
            "ended_at": 3,
            "completed_chapters": [2],
            "failed_chapter": 3,
            "status": "failed",
            "per_chapter_results": [
                {
                    "chapter_no": 3,
                    "status": "failed",
                    "failure_stage": "consistency_check",
                    "artifacts": {
                        "suggestion_path": "D:/tmp/novel/suggestions/ch003.suggestion.json",
                        "review_path": "D:/tmp/novel/reviews/ch003.review.json",
                        "snapshot_path": "D:/tmp/novel/snapshots/ch003.snapshot.json",
                    },
                    "error": "consistency blocked",
                }
            ],
        },
    )
    monkeypatch.setattr(
        phase2_cli,
        "build_project_status_report",
        lambda project_root: {
            "last_failure_stage": "consistency_check",
            "checkpoint_path": "D:/tmp/novel/checkpoints/ch003.checkpoint.json",
            "review_path": "D:/tmp/novel/reviews/ch003.review.json",
            "suggestion_path": "D:/tmp/novel/suggestions/ch003.suggestion.json",
            "snapshot_path": "D:/tmp/novel/snapshots/ch003.snapshot.json",
            "unresolved_snapshot_exists": True,
            "stale_snapshot_exists": False,
        },
    )

    exit_code = phase2_cli.main(["run-five", "--root", "D:/tmp/novel"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "status: failed" in output
    assert "failed_chapter: 3" in output
    assert "failure_stage: consistency_check" in output
    assert "next_check: checkpoint" in output
    assert "checkpoint_path: D:/tmp/novel/checkpoints/ch003.checkpoint.json" in output
    assert "snapshot_path: D:/tmp/novel/snapshots/ch003.snapshot.json" in output


def test_workflow_error_returns_non_zero(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(
        phase2_cli,
        "run_five_chapter_loop",
        lambda project_root: (_ for _ in ()).throw(RuntimeError("loop state missing")),
    )

    exit_code = phase2_cli.main(["run-five", "--root", "D:/tmp/novel"])

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "loop state missing" in output


def _review_cli_payload(chapter_no: int, status: str) -> dict[str, object]:
    return {
        "chapter_no": chapter_no,
        "status": status,
        "review_path": f"D:/tmp/novel/reviews/ch{chapter_no:03d}.review.json",
        "suggestion_path": f"D:/tmp/novel/suggestions/ch{chapter_no:03d}.suggestion.json",
        "approved_suggestion_summary": {
            "chapter_no": chapter_no,
            "character_updates": 1,
            "timeline_updates": 0,
            "foreshadow_updates": 0,
            "notes": "Suggestion only.",
        },
        "consistency_check": {
            "version": 1,
            "checked_at": "2026-03-28T12:00:00Z",
            "blockers": [],
            "warnings": [],
        },
        "review_notes": [],
        "reject_reason": "",
        "approved_at": "2026-03-28T12:01:00Z" if status == "approved" else "",
        "rejected_at": "2026-03-28T12:01:00Z" if status == "rejected" else "",
        "committed_at": "2026-03-28T12:01:00Z" if status == "committed" else "",
        "committed": status == "committed",
        "committed_chapter_no": chapter_no if status == "committed" else None,
    }
