from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

import app


def make_input(values: list[str]) -> app.InputFunc:
    iterator: Iterator[str] = iter(values)

    def fake_input(prompt: str) -> str:
        return next(iterator)

    return fake_input


def test_main_runs_basic_workflow_and_prints_sections_with_previous_summary(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    result: dict[str, Any] = {
        "outline": {"title": "\u661f\u6d77\u56de\u58f0", "theme": "\u9009\u62e9\u4e0e\u4ee3\u4ef7"},
        "chapter_plan": {"chapter_no": 2, "title": "\u96e8\u591c\u542f\u7a0b"},
        "draft": "\u8fd9\u662f\u7b2c\u4e00\u7ae0\u6b63\u6587\u3002",
        "rewritten_draft": None,
    }
    saved_results: list[tuple[str, dict[str, Any]]] = []

    def fake_run_basic_workflow(
        topic: str,
        style: str,
        target: str,
        chapter_no: int = 1,
        previous_summary: str = "",
    ) -> dict[str, Any]:
        assert topic == "\u79d1\u5e7b"
        assert style == "\u51b7\u5cfb"
        assert target == "\u9752\u5e74\u5411 / \u4e2d\u7bc7"
        assert chapter_no == 2
        assert previous_summary == "\u4e0a\u4e00\u7ae0\u6458\u8981"
        return result

    def fake_save_workflow_result(path: str, data: dict[str, Any]) -> bool:
        saved_results.append((path, data))
        return True

    monkeypatch.setattr(app, "run_basic_workflow", fake_run_basic_workflow)
    monkeypatch.setattr(app, "save_workflow_result", fake_save_workflow_result)

    exit_code = app.main(
        make_input(
            [
                "\u79d1\u5e7b",
                "\u51b7\u5cfb",
                "\u9752\u5e74\u5411 / \u4e2d\u7bc7",
                "2",
                "\u4e0a\u4e00\u7ae0\u6458\u8981",
            ]
        )
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "\u751f\u6210\u5b8c\u6210\u3002" in output
    assert "=== \u603b\u7eb2 ===" in output
    assert "=== \u7ae0\u7eb2 ===" in output
    assert "=== \u6b63\u6587 ===" in output
    assert "\u661f\u6d77\u56de\u58f0" in output
    assert "\u8fd9\u662f\u7b2c\u4e00\u7ae0\u6b63\u6587\u3002" in output
    assert "\u7ed3\u679c\u5df2\u4fdd\u5b58\u5230 data/book.json" in output
    assert saved_results == [("data/book.json", result)]


def test_main_prints_clear_error_when_workflow_fails_after_skipping_previous_summary(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_run_basic_workflow(
        topic: str,
        style: str,
        target: str,
        chapter_no: int = 1,
        previous_summary: str = "",
    ) -> dict[str, Any]:
        assert chapter_no == 1
        assert previous_summary == ""
        raise RuntimeError("LLM \u670d\u52a1\u6682\u4e0d\u53ef\u7528")

    monkeypatch.setattr(app, "run_basic_workflow", fake_run_basic_workflow)

    exit_code = app.main(
        make_input(["\u7384\u5e7b", "\u70ed\u8840", "\u5927\u4f17\u5411 / \u957f\u7bc7", "", ""])
    )

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "\u8fd0\u884c\u5931\u8d25: LLM \u670d\u52a1\u6682\u4e0d\u53ef\u7528" in output


def test_main_prints_clear_error_for_non_positive_chapter_number(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_run_basic_workflow(
        topic: str,
        style: str,
        target: str,
        chapter_no: int = 1,
        previous_summary: str = "",
    ) -> dict[str, Any]:
        raise AssertionError("workflow should not run")

    monkeypatch.setattr(app, "run_basic_workflow", fake_run_basic_workflow)

    exit_code = app.main(
        make_input(["\u7384\u5e7b", "\u70ed\u8840", "\u5927\u4f17\u5411 / \u957f\u7bc7", "0"])
    )

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "\u8fd0\u884c\u5931\u8d25: \u7ae0\u8282\u53f7\u5fc5\u987b\u662f\u6b63\u6574\u6570" in output
