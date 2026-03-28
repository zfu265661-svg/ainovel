from __future__ import annotations

import phase1_cli


def test_create_project_command_runs_successfully(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(
        phase1_cli,
        "create_project",
        lambda project_root, title, topic, style, target: {
            "project_id": "novel",
            "title": title,
        },
    )

    exit_code = phase1_cli.main(
        [
            "create-project",
            "--root",
            "D:/tmp/novel",
            "--title",
            "Test Novel",
            "--topic",
            "xianxia",
            "--style",
            "cold",
            "--target",
            "serial",
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "D:/tmp/novel/project.json" in output


def test_plan_novel_command_runs_successfully(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(
        phase1_cli,
        "plan_novel",
        lambda project_root: {
            "outline": {"title": "Test Outline"},
            "chapters": [
                {
                    "chapter_no": 1,
                    "volume_no": 1,
                    "title": "Chapter One",
                    "goal": "Open the story",
                    "status": "planned",
                }
            ],
        },
    )

    exit_code = phase1_cli.main(["plan-novel", "--root", "D:/tmp/novel"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "D:/tmp/novel/docs/outline.md" in output


def test_write_chapter_command_runs_successfully(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(
        phase1_cli,
        "write_chapter",
        lambda project_root, chapter_no: {
            "chapter_no": chapter_no,
            "draft_path": f"{project_root}/docs/ch001.draft.md",
            "rewrite_path": f"{project_root}/docs/ch001.rewrite.md",
            "summary_path": f"{project_root}/docs/ch001.summary.md",
            "suggestion_path": f"{project_root}/suggestions/ch001.suggestion.json",
        },
    )

    exit_code = phase1_cli.main(
        ["write-chapter", "--root", "D:/tmp/novel", "--chapter", "1"]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "D:/tmp/novel/docs/ch001.draft.md" in output


def test_missing_required_argument_returns_non_zero(capsys) -> None:
    exit_code = phase1_cli.main(["create-project", "--root", "D:/tmp/novel"])

    captured = capsys.readouterr()
    assert exit_code != 0
    assert "usage:" in captured.err


def test_workflow_error_returns_non_zero(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(
        phase1_cli,
        "plan_novel",
        lambda project_root: (_ for _ in ()).throw(RuntimeError("disk full")),
    )

    exit_code = phase1_cli.main(["plan-novel", "--root", "D:/tmp/novel"])

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "disk full" in output


def test_commit_suggestion_command_runs_successfully(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(
        phase1_cli,
        "commit_suggestion",
        lambda project_root, chapter_no: {
            "chapter_no": chapter_no,
            "suggestion_path": f"{project_root}/suggestions/ch001.suggestion.json",
            "characters_updated": 1,
            "timeline_updated": 1,
            "foreshadow_updated": 1,
        },
    )
    monkeypatch.setattr(
        phase1_cli,
        "build_chapter_diagnostic_report",
        lambda project_root, chapter_no: {
            "artifact_relation_status": "partial",
            "review_path": f"{project_root}/reviews/ch001.review.json",
            "suggestion_path": f"{project_root}/suggestions/ch001.suggestion.json",
            "snapshot_path": f"{project_root}/snapshots/ch001.snapshot.json",
            "failure_stage": None,
        },
    )

    exit_code = phase1_cli.main(
        ["commit-suggestion", "--root", "D:/tmp/novel", "--chapter", "1"]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "D:/tmp/novel/characters.json" in output
    assert "review_path: D:/tmp/novel/reviews/ch001.review.json" in output
    assert "artifact_relation_status: partial" in output


def test_commit_suggestion_command_prints_diagnostics_when_commit_fails(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(
        phase1_cli,
        "commit_suggestion",
        lambda project_root, chapter_no: (_ for _ in ()).throw(
            RuntimeError("Failed during snapshot cleanup: stale snapshot cleanup blocked")
        ),
    )
    monkeypatch.setattr(
        phase1_cli,
        "build_chapter_diagnostic_report",
        lambda project_root, chapter_no: {
            "artifact_relation_status": "partial",
            "review_path": f"{project_root}/reviews/ch001.review.json",
            "suggestion_path": f"{project_root}/suggestions/ch001.suggestion.json",
            "snapshot_path": f"{project_root}/snapshots/ch001.snapshot.json",
            "failure_stage": "snapshot_cleanup",
        },
    )

    exit_code = phase1_cli.main(
        ["commit-suggestion", "--root", "D:/tmp/novel", "--chapter", "1"]
    )

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "failure_stage: snapshot_cleanup" in output
    assert "review_path: D:/tmp/novel/reviews/ch001.review.json" in output
    assert "snapshot_path: D:/tmp/novel/snapshots/ch001.snapshot.json" in output
    assert "stale snapshot cleanup blocked" in output
