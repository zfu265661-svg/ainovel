from __future__ import annotations

from importlib import import_module
from types import ModuleType
from typing import Any, Callable, Protocol, TypeVar, cast

from core.chapter_service import generate_chapter_plan
from core.draft_service import generate_draft
from core.errors import NovelAgentError
from core.outline_service import generate_outline
from core.timeline_service import load_timeline


class WorkflowServiceError(NovelAgentError, RuntimeError):
    """Raised when the basic novel workflow fails."""


class _RewriteModule(Protocol):
    def rewrite_text(self, text: str) -> str:
        ...


class _CheckerModule(Protocol):
    def check_consistency(
        self,
        draft_text: str,
        outline: dict[str, Any],
        character_info: dict[str, Any],
        timeline: list[Any],
    ) -> dict[str, Any]:
        ...


class _StorageModule(Protocol):
    def save_json(self, path: str, data: dict[str, Any]) -> None:
        ...


T = TypeVar("T")


def run_basic_workflow(
    topic: str,
    style: str,
    target: str,
    chapter_no: int = 1,
    previous_summary: str = "",
) -> dict[str, Any]:
    """Run the minimum novel workflow from outline generation to optional rewrite."""
    outline = _generate_outline_stage(
        topic=topic,
        style=style,
        target=target,
    )
    chapter_plan = _generate_chapter_plan_stage(
        outline=outline,
        chapter_no=chapter_no,
        previous_summary=previous_summary,
    )
    draft = _generate_draft_stage(
        chapter_plan=chapter_plan,
        outline=outline,
        style=style,
    )
    rewritten_draft = _rewrite_draft_if_available(draft)

    return _build_workflow_result(
        outline=outline,
        chapter_plan=chapter_plan,
        draft=draft,
        rewritten_draft=rewritten_draft,
    )


def run_basic_workflow_with_consistency_check(
    topic: str,
    style: str,
    target: str,
    chapter_no: int = 1,
    previous_summary: str = "",
) -> dict[str, Any]:
    """Run the basic workflow and append a consistency check result."""
    result = run_basic_workflow(
        topic=topic,
        style=style,
        target=target,
        chapter_no=chapter_no,
        previous_summary=previous_summary,
    )
    consistency_check = _run_consistency_check_stage(result)
    return _attach_consistency_check(result, consistency_check)


def save_workflow_result(path: str, result: dict[str, Any]) -> bool:
    """Persist workflow output if the optional storage module is available."""
    storage_module = _load_optional_module("core.storage")
    if storage_module is None:
        return False

    typed_storage = cast(_StorageModule, storage_module)
    try:
        typed_storage.save_json(path, result)
    except Exception as exc:
        raise WorkflowServiceError(
            f"Failed to save workflow result to '{path}': {exc}"
        ) from exc

    return True


def _generate_outline_stage(topic: str, style: str, target: str) -> dict[str, Any]:
    return _run_stage(
        "outline generation",
        lambda: generate_outline(topic=topic, style=style, target=target),
    )


def _generate_chapter_plan_stage(
    outline: dict[str, Any],
    chapter_no: int,
    previous_summary: str,
) -> dict[str, Any]:
    return _run_stage(
        "chapter plan generation",
        lambda: generate_chapter_plan(
            outline=outline,
            chapter_no=chapter_no,
            previous_summary=previous_summary,
        ),
    )


def _generate_draft_stage(
    chapter_plan: dict[str, Any],
    outline: dict[str, Any],
    style: str,
) -> str:
    return _run_stage(
        "draft generation",
        lambda: generate_draft(
            chapter_plan=chapter_plan,
            character_info=_project_protagonist(outline),
            style_rules=style,
        ),
    )


def _run_stage(stage_name: str, action: Callable[[], T]) -> T:
    try:
        return action()
    except WorkflowServiceError:
        raise
    except Exception as exc:
        raise WorkflowServiceError(f"Failed during {stage_name}: {exc}") from exc


def _rewrite_draft_if_available(draft: str) -> str | None:
    rewrite_module = _load_optional_rewrite_module()
    if rewrite_module is None:
        return None

    return _run_stage("draft rewrite", lambda: rewrite_module.rewrite_text(draft))


def _run_consistency_check_stage(result: dict[str, Any]) -> dict[str, Any]:
    checker_module = _load_checker_module()
    return _run_stage(
        "consistency check",
        lambda: checker_module.check_consistency(
            draft_text=_select_draft_for_consistency_check(result),
            outline=result["outline"],
            character_info=_project_protagonist(result["outline"]),
            timeline=_load_timeline_history(result),
        ),
    )


def _load_optional_rewrite_module() -> _RewriteModule | None:
    rewrite_module = _load_optional_module("core.rewrite_service")
    if rewrite_module is None:
        return None
    return cast(_RewriteModule, rewrite_module)


def _load_checker_module() -> _CheckerModule:
    checker_module = _load_optional_module("core.checker_service")
    if checker_module is None:
        raise WorkflowServiceError("Failed during consistency check: checker service is not available.")
    return cast(_CheckerModule, checker_module)


def _project_protagonist(outline: dict[str, Any]) -> dict[str, Any]:
    protagonist = outline.get("protagonist")
    if isinstance(protagonist, dict):
        return protagonist
    return {}


def _select_draft_for_consistency_check(result: dict[str, Any]) -> str:
    rewritten_draft = result.get("rewritten_draft")
    if isinstance(rewritten_draft, str) and rewritten_draft:
        return rewritten_draft
    return cast(str, result["draft"])


def _load_timeline_history(result: dict[str, Any]) -> list[Any]:
    chapter_no = _extract_chapter_no(result.get("chapter_plan"))
    try:
        timeline = load_timeline()
    except FileNotFoundError:
        return []

    if chapter_no is None:
        return timeline

    return [
        event
        for event in timeline
        if isinstance(event, dict) and event.get("chapter_no") is not None and event.get("chapter_no") < chapter_no
    ]


def _extract_chapter_no(chapter_plan: Any) -> int | None:
    if not isinstance(chapter_plan, dict):
        return None

    chapter_no = chapter_plan.get("chapter_no")
    if isinstance(chapter_no, int):
        return chapter_no

    return None


def _build_workflow_result(
    outline: dict[str, Any],
    chapter_plan: dict[str, Any],
    draft: str,
    rewritten_draft: str | None,
) -> dict[str, Any]:
    return {
        "outline": outline,
        "chapter_plan": chapter_plan,
        "draft": draft,
        "rewritten_draft": rewritten_draft,
    }


def _attach_consistency_check(
    result: dict[str, Any],
    consistency_check: dict[str, Any],
) -> dict[str, Any]:
    return {
        **result,
        "consistency_check": consistency_check,
    }


def _load_optional_module(module_name: str) -> ModuleType | None:
    try:
        return import_module(module_name)
    except ModuleNotFoundError as exc:
        if exc.name == module_name:
            return None
        raise
