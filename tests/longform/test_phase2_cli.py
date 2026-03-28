from __future__ import annotations

import phase2_cli


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
            "last_attempted_chapter_no": 3,
            "last_attempt_status": "ready",
            "last_failure_stage": None,
            "last_error": None,
            "unresolved_snapshot_exists": False,
            "unresolved_snapshot_chapters": [],
            "stale_snapshot_exists": False,
            "stale_snapshot_chapters": [],
            "artifact_focus_chapter_no": 3,
            "artifact_relation_status": "partial",
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
    assert "artifact_relation_status: partial" in output
    assert "review_path: D:/tmp/novel/reviews/ch003.review.json" in output


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
