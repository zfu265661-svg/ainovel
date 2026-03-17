from __future__ import annotations

from types import ModuleType

import pytest

from core.timeline_service import TimelineValidationError
from core.workflow_service import (
    WorkflowServiceError,
    run_basic_workflow,
    run_basic_workflow_with_consistency_check,
    save_workflow_result,
)


def test_run_basic_workflow_returns_full_result_and_passes_chapter_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    outline = {
        "title": "test novel",
        "protagonist": {"name": "Lin Lan"},
    }
    chapter_plan = {
        "chapter_no": 1,
        "title": "chapter one",
    }

    monkeypatch.setattr(
        "core.workflow_service.generate_outline",
        lambda topic, style, target: outline,
    )

    def fake_generate_chapter_plan(
        outline: dict[str, object],
        chapter_no: int,
        previous_summary: str,
    ) -> dict[str, object]:
        assert outline == {
            "title": "test novel",
            "protagonist": {"name": "Lin Lan"},
        }
        assert chapter_no == 2
        assert previous_summary == "previous summary"
        return chapter_plan

    monkeypatch.setattr(
        "core.workflow_service.generate_chapter_plan",
        fake_generate_chapter_plan,
    )

    def fake_generate_draft(
        chapter_plan: dict[str, object],
        character_info: dict[str, object],
        style_rules: str,
    ) -> str:
        assert chapter_plan == {"chapter_no": 1, "title": "chapter one"}
        assert character_info == {"name": "Lin Lan"}
        assert style_rules == "cold"
        return "draft text"

    monkeypatch.setattr("core.workflow_service.generate_draft", fake_generate_draft)

    rewrite_module = ModuleType("core.rewrite_service")
    rewrite_module.rewrite_text = lambda text: f"rewrite:{text}"  # type: ignore[attr-defined]
    monkeypatch.setattr(
        "core.workflow_service._load_optional_module",
        lambda module_name: rewrite_module
        if module_name == "core.rewrite_service"
        else None,
    )

    result = run_basic_workflow(
        "xianxia",
        "cold",
        "serial",
        chapter_no=2,
        previous_summary="previous summary",
    )

    assert result == {
        "outline": outline,
        "chapter_plan": chapter_plan,
        "draft": "draft text",
        "rewritten_draft": "rewrite:draft text",
    }


def test_run_basic_workflow_keeps_compatible_behavior_when_previous_summary_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "core.workflow_service.generate_outline",
        lambda topic, style, target: {"protagonist": {"name": "Lin Lan"}},
    )

    def fake_generate_chapter_plan(outline, chapter_no, previous_summary):
        assert previous_summary == ""
        return {"chapter_no": 1}

    monkeypatch.setattr(
        "core.workflow_service.generate_chapter_plan",
        fake_generate_chapter_plan,
    )
    monkeypatch.setattr(
        "core.workflow_service.generate_draft",
        lambda chapter_plan, character_info, style_rules: "draft text",
    )
    monkeypatch.setattr(
        "core.workflow_service._load_optional_module",
        lambda module_name: None,
    )

    result = run_basic_workflow("xianxia", "cold", "serial")

    assert result["rewritten_draft"] is None


def test_run_basic_workflow_keeps_default_chapter_number_when_not_provided(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "core.workflow_service.generate_outline",
        lambda topic, style, target: {"protagonist": {"name": "Lin Lan"}},
    )

    def fake_generate_chapter_plan(outline, chapter_no, previous_summary):
        assert chapter_no == 1
        assert previous_summary == ""
        return {"chapter_no": chapter_no}

    monkeypatch.setattr(
        "core.workflow_service.generate_chapter_plan",
        fake_generate_chapter_plan,
    )
    monkeypatch.setattr(
        "core.workflow_service.generate_draft",
        lambda chapter_plan, character_info, style_rules: "draft text",
    )
    monkeypatch.setattr(
        "core.workflow_service._load_optional_module",
        lambda module_name: None,
    )

    result = run_basic_workflow("xianxia", "cold", "serial")

    assert result["chapter_plan"]["chapter_no"] == 1


def test_run_basic_workflow_wraps_key_service_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_generate_outline(topic: str, style: str, target: str) -> dict[str, object]:
        raise ValueError("LLM timeout")

    monkeypatch.setattr(
        "core.workflow_service.generate_outline",
        fake_generate_outline,
    )

    with pytest.raises(
        WorkflowServiceError,
        match="Failed during outline generation: LLM timeout",
    ):
        run_basic_workflow("xianxia", "cold", "serial")


def test_save_workflow_result_returns_false_when_storage_module_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "core.workflow_service._load_optional_module",
        lambda module_name: None,
    )

    saved = save_workflow_result("data/book.json", {"outline": {"title": "test"}})

    assert saved is False


def test_save_workflow_result_saves_data_when_storage_module_is_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    saved_calls: list[tuple[str, dict[str, object]]] = []
    storage_module = ModuleType("core.storage")

    def fake_save_json(path: str, data: dict[str, object]) -> None:
        saved_calls.append((path, data))

    storage_module.save_json = fake_save_json  # type: ignore[attr-defined]
    monkeypatch.setattr(
        "core.workflow_service._load_optional_module",
        lambda module_name: storage_module
        if module_name == "core.storage"
        else None,
    )

    result = {"outline": {"title": "test"}}
    saved = save_workflow_result("data/book.json", result)

    assert saved is True
    assert saved_calls == [("data/book.json", result)]


def test_save_workflow_result_wraps_storage_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    storage_module = ModuleType("core.storage")

    def fake_save_json(path: str, data: dict[str, object]) -> None:
        raise OSError("disk full")

    storage_module.save_json = fake_save_json  # type: ignore[attr-defined]
    monkeypatch.setattr(
        "core.workflow_service._load_optional_module",
        lambda module_name: storage_module
        if module_name == "core.storage"
        else None,
    )

    with pytest.raises(
        WorkflowServiceError,
        match="Failed to save workflow result to 'data/book.json': disk full",
    ):
        save_workflow_result("data/book.json", {"outline": {"title": "test"}})


def test_run_basic_workflow_with_consistency_check_uses_rewritten_draft_when_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base_result = {
        "outline": {"title": "test novel", "protagonist": {"name": "Lin Lan"}},
        "chapter_plan": {"chapter_no": 1, "title": "chapter one"},
        "draft": "draft text",
        "rewritten_draft": "rewritten text",
    }
    checker_module = ModuleType("core.checker_service")

    def fake_check_consistency(
        draft_text: str,
        outline: dict[str, object],
        character_info: dict[str, object],
        timeline: list[object],
    ) -> dict[str, object]:
        assert draft_text == "rewritten text"
        assert outline == base_result["outline"]
        assert character_info == {"name": "Lin Lan"}
        assert timeline == []
        return {"has_issue": False, "issues": [], "suggestions": []}

    checker_module.check_consistency = fake_check_consistency  # type: ignore[attr-defined]
    monkeypatch.setattr("core.workflow_service.load_timeline", lambda: [])
    monkeypatch.setattr(
        "core.workflow_service.run_basic_workflow",
        lambda topic, style, target, chapter_no=1, previous_summary="": base_result,
    )
    monkeypatch.setattr(
        "core.workflow_service._load_optional_module",
        lambda module_name: checker_module
        if module_name == "core.checker_service"
        else None,
    )

    result = run_basic_workflow_with_consistency_check("xianxia", "cold", "serial")

    assert result == {
        **base_result,
        "consistency_check": {"has_issue": False, "issues": [], "suggestions": []},
    }


def test_run_basic_workflow_with_consistency_check_falls_back_to_draft_when_no_rewrite(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base_result = {
        "outline": {"title": "test novel", "protagonist": {"name": "Lin Lan"}},
        "chapter_plan": {"chapter_no": 1, "title": "chapter one"},
        "draft": "draft text",
        "rewritten_draft": None,
    }
    checker_module = ModuleType("core.checker_service")

    def fake_check_consistency(
        draft_text: str,
        outline: dict[str, object],
        character_info: dict[str, object],
        timeline: list[object],
    ) -> dict[str, object]:
        assert draft_text == "draft text"
        assert outline == base_result["outline"]
        assert character_info == {"name": "Lin Lan"}
        assert timeline == []
        return {"has_issue": True, "issues": ["timeline"], "suggestions": ["fix"]}

    checker_module.check_consistency = fake_check_consistency  # type: ignore[attr-defined]
    monkeypatch.setattr("core.workflow_service.load_timeline", lambda: [])
    monkeypatch.setattr(
        "core.workflow_service.run_basic_workflow",
        lambda topic, style, target, chapter_no=1, previous_summary="": base_result,
    )
    monkeypatch.setattr(
        "core.workflow_service._load_optional_module",
        lambda module_name: checker_module
        if module_name == "core.checker_service"
        else None,
    )

    result = run_basic_workflow_with_consistency_check("xianxia", "cold", "serial")

    assert result["consistency_check"] == {
        "has_issue": True,
        "issues": ["timeline"],
        "suggestions": ["fix"],
    }


def test_run_basic_workflow_with_consistency_check_wraps_checker_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base_result = {
        "outline": {"title": "test novel", "protagonist": {"name": "Lin Lan"}},
        "chapter_plan": {"chapter_no": 1, "title": "chapter one"},
        "draft": "draft text",
        "rewritten_draft": None,
    }
    checker_module = ModuleType("core.checker_service")
    checker_module.check_consistency = lambda **kwargs: (_ for _ in ()).throw(ValueError("bad check"))  # type: ignore[attr-defined]

    monkeypatch.setattr("core.workflow_service.load_timeline", lambda: [])
    monkeypatch.setattr(
        "core.workflow_service.run_basic_workflow",
        lambda topic, style, target, chapter_no=1, previous_summary="": base_result,
    )
    monkeypatch.setattr(
        "core.workflow_service._load_optional_module",
        lambda module_name: checker_module
        if module_name == "core.checker_service"
        else None,
    )

    with pytest.raises(
        WorkflowServiceError,
        match="Failed during consistency check: bad check",
    ):
        run_basic_workflow_with_consistency_check("xianxia", "cold", "serial")


def test_run_basic_workflow_with_consistency_check_uses_only_previous_timeline_events(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base_result = {
        "outline": {"title": "test novel", "protagonist": {"name": "Lin Lan"}},
        "chapter_plan": {"chapter_no": 3, "title": "chapter three"},
        "draft": "draft text",
        "rewritten_draft": None,
    }
    timeline_events = [
        {"id": "evt-1", "chapter_no": 1, "event": "chapter one event"},
        {"id": "evt-2", "chapter_no": 2, "event": "chapter two event"},
        {"id": "evt-3", "chapter_no": 3, "event": "current chapter event"},
        {"id": "evt-4", "chapter_no": 4, "event": "future event"},
    ]
    checker_module = ModuleType("core.checker_service")

    def fake_check_consistency(
        draft_text: str,
        outline: dict[str, object],
        character_info: dict[str, object],
        timeline: list[object],
    ) -> dict[str, object]:
        assert draft_text == "draft text"
        assert outline == base_result["outline"]
        assert character_info == {"name": "Lin Lan"}
        assert timeline == [
            {"id": "evt-1", "chapter_no": 1, "event": "chapter one event"},
            {"id": "evt-2", "chapter_no": 2, "event": "chapter two event"},
        ]
        return {"has_issue": False, "issues": [], "suggestions": []}

    checker_module.check_consistency = fake_check_consistency  # type: ignore[attr-defined]
    monkeypatch.setattr("core.workflow_service.load_timeline", lambda: timeline_events)
    monkeypatch.setattr(
        "core.workflow_service.run_basic_workflow",
        lambda topic, style, target, chapter_no=1, previous_summary="": base_result,
    )
    monkeypatch.setattr(
        "core.workflow_service._load_optional_module",
        lambda module_name: checker_module
        if module_name == "core.checker_service"
        else None,
    )

    result = run_basic_workflow_with_consistency_check("xianxia", "cold", "serial")

    assert result["consistency_check"] == {
        "has_issue": False,
        "issues": [],
        "suggestions": [],
    }


def test_run_basic_workflow_with_consistency_check_falls_back_to_empty_timeline_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base_result = {
        "outline": {"title": "test novel", "protagonist": {"name": "Lin Lan"}},
        "chapter_plan": {"chapter_no": 2, "title": "chapter two"},
        "draft": "draft text",
        "rewritten_draft": None,
    }
    checker_module = ModuleType("core.checker_service")

    def fake_check_consistency(
        draft_text: str,
        outline: dict[str, object],
        character_info: dict[str, object],
        timeline: list[object],
    ) -> dict[str, object]:
        assert timeline == []
        return {"has_issue": False, "issues": [], "suggestions": []}

    checker_module.check_consistency = fake_check_consistency  # type: ignore[attr-defined]
    monkeypatch.setattr(
        "core.workflow_service.load_timeline",
        lambda: (_ for _ in ()).throw(FileNotFoundError("missing timeline")),
    )
    monkeypatch.setattr(
        "core.workflow_service.run_basic_workflow",
        lambda topic, style, target, chapter_no=1, previous_summary="": base_result,
    )
    monkeypatch.setattr(
        "core.workflow_service._load_optional_module",
        lambda module_name: checker_module
        if module_name == "core.checker_service"
        else None,
    )

    result = run_basic_workflow_with_consistency_check("xianxia", "cold", "serial")

    assert result["consistency_check"] == {
        "has_issue": False,
        "issues": [],
        "suggestions": [],
    }


def test_run_basic_workflow_with_consistency_check_wraps_invalid_timeline_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base_result = {
        "outline": {"title": "test novel", "protagonist": {"name": "Lin Lan"}},
        "chapter_plan": {"chapter_no": 2, "title": "chapter two"},
        "draft": "draft text",
        "rewritten_draft": None,
    }
    checker_module = ModuleType("core.checker_service")
    checker_module.check_consistency = lambda **kwargs: {"has_issue": False, "issues": [], "suggestions": []}  # type: ignore[attr-defined]

    monkeypatch.setattr(
        "core.workflow_service.load_timeline",
        lambda: (_ for _ in ()).throw(
            TimelineValidationError("Timeline data file must contain a JSON array: data/timeline.json")
        ),
    )
    monkeypatch.setattr(
        "core.workflow_service.run_basic_workflow",
        lambda topic, style, target, chapter_no=1, previous_summary="": base_result,
    )
    monkeypatch.setattr(
        "core.workflow_service._load_optional_module",
        lambda module_name: checker_module
        if module_name == "core.checker_service"
        else None,
    )

    with pytest.raises(
        WorkflowServiceError,
        match="Failed during consistency check: Timeline data file must contain a JSON array: data/timeline.json",
    ):
        run_basic_workflow_with_consistency_check("xianxia", "cold", "serial")
