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
    assert "初始化完成。" in output
    assert "项目路径: D:/tmp/novel" in output
    assert "目标章节数: 5" in output


def test_show_status_command_prints_current_loop_state(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(
        phase2_cli,
        "load_project_loop_state",
        lambda project_root: {
            "status": "ready",
            "start_chapter_no": 1,
            "target_chapter_count": 5,
            "next_chapter_no": 3,
            "last_completed_chapter_no": 2,
            "current_chapter_no": None,
        },
    )

    exit_code = phase2_cli.main(["show-status", "--root", "D:/tmp/novel"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "当前状态。" in output
    assert "状态: ready" in output
    assert "下一章节: 3" in output
    assert "已完成到: 2" in output


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
    assert "运行结束。" in output
    assert "开始章节: 1" in output
    assert "结束章节: 5" in output
    assert "状态: completed" in output
    assert "完成章节数: 5" in output


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
            "per_chapter_results": [],
        },
    )

    exit_code = phase2_cli.main(["run-five", "--root", "D:/tmp/novel"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "状态: failed" in output
    assert "失败章节: 3" in output


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
    assert "运行失败: loop state missing" in output
