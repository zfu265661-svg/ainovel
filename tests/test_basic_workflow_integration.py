from __future__ import annotations

import importlib
from importlib.util import find_spec
from types import ModuleType
from typing import Any

import pytest


if find_spec("core.workflow_service") is None:
    pytest.skip("core.workflow_service is not available", allow_module_level=True)

workflow_service = importlib.import_module("core.workflow_service")


def test_run_basic_workflow_returns_outline_chapter_plan_and_draft(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    call_order: list[str] = []
    outline: dict[str, Any] = {
        "title": "Smoke Novel",
        "protagonist": {"name": "Lin Chen"},
    }
    chapter_plan: dict[str, Any] = {
        "chapter_no": 1,
        "title": "Chapter 1",
    }

    def fake_generate_outline(topic: str, style: str, target: str) -> dict[str, Any]:
        call_order.append("outline")
        assert topic == "xianxia"
        assert style == "cold"
        assert target == "serial"
        return outline

    def fake_generate_chapter_plan(
        outline: dict[str, Any],
        chapter_no: int,
        previous_summary: str,
    ) -> dict[str, Any]:
        call_order.append("chapter_plan")
        assert outline == {
            "title": "Smoke Novel",
            "protagonist": {"name": "Lin Chen"},
        }
        assert chapter_no == 1
        assert previous_summary == ""
        return chapter_plan

    def fake_generate_draft(
        chapter_plan: dict[str, Any],
        character_info: dict[str, Any],
        style_rules: str,
    ) -> str:
        call_order.append("draft")
        assert chapter_plan == {
            "chapter_no": 1,
            "title": "Chapter 1",
        }
        assert character_info == {"name": "Lin Chen"}
        assert style_rules == "cold"
        return "draft body"

    monkeypatch.setattr(workflow_service, "generate_outline", fake_generate_outline)
    monkeypatch.setattr(
        workflow_service,
        "generate_chapter_plan",
        fake_generate_chapter_plan,
    )
    monkeypatch.setattr(workflow_service, "generate_draft", fake_generate_draft)
    monkeypatch.setattr(
        workflow_service,
        "_load_optional_module",
        lambda module_name: None,
    )

    result = workflow_service.run_basic_workflow("xianxia", "cold", "serial")

    assert call_order == ["outline", "chapter_plan", "draft"]
    assert result["outline"] == outline
    assert result["chapter_plan"] == chapter_plan
    assert result["draft"] == "draft body"
    assert set(result) >= {"outline", "chapter_plan", "draft"}


def test_run_basic_workflow_allows_previous_summary_in_main_chain(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        workflow_service,
        "generate_outline",
        lambda topic, style, target: {"protagonist": {"name": "Lin Chen"}},
    )

    def fake_generate_chapter_plan(
        outline: dict[str, Any],
        chapter_no: int,
        previous_summary: str,
    ) -> dict[str, Any]:
        assert outline == {"protagonist": {"name": "Lin Chen"}}
        assert chapter_no == 3
        assert previous_summary == "previous chapter summary"
        return {"chapter_no": 3, "title": "Chapter 3"}

    monkeypatch.setattr(
        workflow_service,
        "generate_chapter_plan",
        fake_generate_chapter_plan,
    )
    monkeypatch.setattr(
        workflow_service,
        "generate_draft",
        lambda chapter_plan, character_info, style_rules: "draft body",
    )
    monkeypatch.setattr(
        workflow_service,
        "_load_optional_module",
        lambda module_name: None,
    )

    result = workflow_service.run_basic_workflow(
        "xianxia",
        "cold",
        "serial",
        chapter_no=3,
        previous_summary="previous chapter summary",
    )

    assert result["chapter_plan"]["title"] == "Chapter 3"
    assert result["draft"] == "draft body"


def test_run_basic_workflow_uses_optional_rewrite_without_real_requests(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        workflow_service,
        "generate_outline",
        lambda topic, style, target: {"protagonist": {"name": "Lin Chen"}},
    )
    monkeypatch.setattr(
        workflow_service,
        "generate_chapter_plan",
        lambda outline, chapter_no, previous_summary: {"chapter_no": 1},
    )
    monkeypatch.setattr(
        workflow_service,
        "generate_draft",
        lambda chapter_plan, character_info, style_rules: "draft body",
    )

    rewrite_module = ModuleType("core.rewrite_service")
    rewrite_module.rewrite_text = lambda text: f"rewrite:{text}"  # type: ignore[attr-defined]
    monkeypatch.setattr(
        workflow_service,
        "_load_optional_module",
        lambda module_name: rewrite_module
        if module_name == "core.rewrite_service"
        else None,
    )

    result = workflow_service.run_basic_workflow("xianxia", "cold", "serial")

    assert result["outline"]["protagonist"]["name"] == "Lin Chen"
    assert result["chapter_plan"]["chapter_no"] == 1
    assert result["draft"] == "draft body"
    assert result["rewritten_draft"] == "rewrite:draft body"
