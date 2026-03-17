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


def test_prompt_user_uses_readable_chinese_prompts() -> None:
    prompts: list[str] = []

    def fake_input(prompt: str) -> str:
        prompts.append(prompt)
        return " value "

    topic, style, target = app.prompt_user(fake_input)

    assert (topic, style, target) == ("value", "value", "value")
    assert prompts == [
        "\u8bf7\u8f93\u5165\u9898\u6750: ",
        "\u8bf7\u8f93\u5165\u98ce\u683c: ",
        "\u8bf7\u8f93\u5165\u76ee\u6807\u8bfb\u8005/\u7bc7\u5e45\u65b9\u5411: ",
    ]


def test_prompt_previous_summary_allows_empty_input() -> None:
    prompts: list[str] = []

    def fake_input(prompt: str) -> str:
        prompts.append(prompt)
        return "   "

    previous_summary = app.prompt_previous_summary(fake_input)

    assert previous_summary == ""
    assert prompts == [
        "\u8bf7\u8f93\u5165\u4e0a\u4e00\u7ae0\u6458\u8981\uff08\u53ef\u9009\uff0c\u76f4\u63a5\u56de\u8f66\u8df3\u8fc7\uff09: "
    ]


def test_prompt_chapter_no_defaults_to_one_when_skipped() -> None:
    prompts: list[str] = []

    def fake_input(prompt: str) -> str:
        prompts.append(prompt)
        return "   "

    chapter_no = app.prompt_chapter_no(fake_input)

    assert chapter_no == 1
    assert prompts == ["\u8bf7\u8f93\u5165\u7ae0\u8282\u53f7\uff08\u53ef\u9009\uff0c\u9ed8\u8ba4 1\uff09: "]


def test_prompt_chapter_no_rejects_invalid_value() -> None:
    with pytest.raises(ValueError, match="\u7ae0\u8282\u53f7\u5fc5\u987b\u662f\u6b63\u6574\u6570"):
        app.prompt_chapter_no(lambda prompt: "0")


def test_main_runs_workflow_and_saves_result_with_previous_summary(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    result: dict[str, Any] = {
        "outline": {"title": "Star Frontier"},
        "chapter_plan": {"chapter_no": 2, "title": "Opening Signal"},
        "draft": "Draft body",
        "rewritten_draft": "Rewritten draft body",
    }
    saved_results: list[tuple[str, dict[str, Any]]] = []

    def fake_run_basic_workflow(
        topic: str,
        style: str,
        target: str,
        chapter_no: int = 1,
        previous_summary: str = "",
    ) -> dict[str, Any]:
        assert topic == "Sci-Fi"
        assert style == "Suspense"
        assert target == "Young adult / novella"
        assert chapter_no == 2
        assert previous_summary == "Previously on the story"
        return result

    def fake_save_workflow_result(path: str, data: dict[str, Any]) -> bool:
        saved_results.append((path, data))
        return True

    monkeypatch.setattr(app, "run_basic_workflow", fake_run_basic_workflow)
    monkeypatch.setattr(app, "save_workflow_result", fake_save_workflow_result)

    exit_code = app.main(
        make_input(
            [
                "Sci-Fi",
                "Suspense",
                "Young adult / novella",
                "2",
                "Previously on the story",
            ]
        )
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Star Frontier" in output
    assert "Rewritten draft body" in output
    assert saved_results == [("data/book.json", result)]


def test_main_runs_workflow_when_previous_summary_is_skipped(
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
        assert topic == "Fantasy"
        assert style == "Epic"
        assert target == "Adult / long-form"
        assert chapter_no == 1
        assert previous_summary == ""
        return {
            "outline": {"title": "Star Frontier"},
            "chapter_plan": {"chapter_no": 1},
            "draft": "Draft body",
            "rewritten_draft": None,
        }

    monkeypatch.setattr(app, "run_basic_workflow", fake_run_basic_workflow)

    exit_code = app.main(make_input(["Fantasy", "Epic", "Adult / long-form", "", ""]))

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Draft body" in output


def test_main_prints_clear_error_when_workflow_fails(
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
        raise RuntimeError("LLM service unavailable")

    monkeypatch.setattr(app, "run_basic_workflow", fake_run_basic_workflow)

    exit_code = app.main(make_input(["Fantasy", "Epic", "Adult / long-form", "", ""]))

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "LLM service unavailable" in output


def test_main_prints_clear_error_when_chapter_number_is_invalid(
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

    exit_code = app.main(make_input(["Fantasy", "Epic", "Adult / long-form", "abc"]))

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "\u8fd0\u884c\u5931\u8d25: \u7ae0\u8282\u53f7\u5fc5\u987b\u662f\u6b63\u6574\u6570" in output


def test_persist_result_prints_clear_error_when_save_fails(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_save_workflow_result(path: str, data: dict[str, Any]) -> bool:
        raise RuntimeError("disk full")

    monkeypatch.setattr(app, "save_workflow_result", fake_save_workflow_result)

    app.persist_result({"outline": {"title": "Star Frontier"}})

    output = capsys.readouterr().out
    assert "disk full" in output


def test_render_section_uses_readable_placeholder_for_missing_content() -> None:
    output = app.render_section("\u6b63\u6587", None)

    assert output == "=== \u6b63\u6587 ===\n\u672a\u751f\u6210"
