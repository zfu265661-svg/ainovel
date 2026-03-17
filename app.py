from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from core.workflow_service import run_basic_workflow, save_workflow_result

InputFunc = Callable[[str], str]
SAVE_PATH = "data/book.json"
PROMPT_TOPIC = "\u8bf7\u8f93\u5165\u9898\u6750: "
PROMPT_STYLE = "\u8bf7\u8f93\u5165\u98ce\u683c: "
PROMPT_TARGET = "\u8bf7\u8f93\u5165\u76ee\u6807\u8bfb\u8005/\u7bc7\u5e45\u65b9\u5411: "
PROMPT_CHAPTER_NO = "\u8bf7\u8f93\u5165\u7ae0\u8282\u53f7\uff08\u53ef\u9009\uff0c\u9ed8\u8ba4 1\uff09: "
PROMPT_PREVIOUS_SUMMARY = (
    "\u8bf7\u8f93\u5165\u4e0a\u4e00\u7ae0\u6458\u8981\uff08\u53ef\u9009\uff0c\u76f4\u63a5\u56de\u8f66\u8df3\u8fc7\uff09: "
)
TEXT_NOT_GENERATED = "\u672a\u751f\u6210"
TEXT_GENERATED = "\u751f\u6210\u5b8c\u6210\u3002"
TEXT_SAVE_FAILED = "\u4fdd\u5b58\u7ed3\u679c\u5931\u8d25"
TEXT_SAVED = "\u7ed3\u679c\u5df2\u4fdd\u5b58\u5230"
TEXT_RUN_FAILED = "\u8fd0\u884c\u5931\u8d25"
TEXT_INVALID_CHAPTER_NO = "\u7ae0\u8282\u53f7\u5fc5\u987b\u662f\u6b63\u6574\u6570"
SECTION_OUTLINE = "\u603b\u7eb2"
SECTION_CHAPTER_PLAN = "\u7ae0\u7eb2"
SECTION_DRAFT = "\u6b63\u6587"


def collect_workflow_inputs(input_func: InputFunc) -> dict[str, Any]:
    """Collect all CLI inputs required by the basic workflow."""
    topic, style, target = prompt_user(input_func)
    return {
        "topic": topic,
        "style": style,
        "target": target,
        "chapter_no": prompt_chapter_no(input_func),
        "previous_summary": prompt_previous_summary(input_func),
    }


def prompt_user(input_func: InputFunc) -> tuple[str, str, str]:
    """Collect the minimum inputs required to run the novel workflow."""
    topic = input_func(PROMPT_TOPIC).strip()
    style = input_func(PROMPT_STYLE).strip()
    target = input_func(PROMPT_TARGET).strip()
    return topic, style, target


def prompt_previous_summary(input_func: InputFunc) -> str:
    """Collect the optional summary of the previous chapter."""
    return input_func(PROMPT_PREVIOUS_SUMMARY).strip()


def prompt_chapter_no(input_func: InputFunc) -> int:
    """Collect the optional chapter number and validate it."""
    raw_value = input_func(PROMPT_CHAPTER_NO).strip()
    if raw_value == "":
        return 1

    try:
        chapter_no = int(raw_value)
    except ValueError as exc:
        raise ValueError(TEXT_INVALID_CHAPTER_NO) from exc

    if chapter_no <= 0:
        raise ValueError(TEXT_INVALID_CHAPTER_NO)

    return chapter_no


def render_section(title: str, data: Any) -> str:
    """Convert one workflow section into readable terminal output."""
    if data is None:
        body = TEXT_NOT_GENERATED
    elif isinstance(data, str):
        body = data
    else:
        body = json.dumps(data, ensure_ascii=False, indent=2)
    return f"=== {title} ===\n{body}"


def render_workflow_result(result: dict[str, Any]) -> str:
    """Format the workflow result for terminal display."""
    sections = [
        render_section(SECTION_OUTLINE, result.get("outline")),
        render_section(SECTION_CHAPTER_PLAN, result.get("chapter_plan")),
        render_section(SECTION_DRAFT, result.get("rewritten_draft") or result.get("draft")),
    ]
    return "\n\n".join(sections)


def print_workflow_result(result: dict[str, Any]) -> None:
    """Print workflow completion status and rendered content."""
    print(TEXT_GENERATED)
    print(render_workflow_result(result))


def render_save_success(path: str) -> str:
    """Return the success message shown after a persisted workflow run."""
    return f"{TEXT_SAVED} {path}"


def handle_save_error(exc: Exception) -> None:
    """Print the save failure message without interrupting the CLI flow."""
    print(f"{TEXT_SAVE_FAILED}: {exc}")


def handle_run_error(exc: Exception) -> int:
    """Print the run failure message and return the CLI error code."""
    print(f"{TEXT_RUN_FAILED}: {exc}")
    return 1


def persist_result(result: dict[str, Any]) -> None:
    """Persist the workflow output when optional storage support is available."""
    try:
        saved = save_workflow_result(SAVE_PATH, result)
    except Exception as exc:
        handle_save_error(exc)
        return

    if saved:
        print(render_save_success(SAVE_PATH))


def main(input_func: InputFunc | None = None) -> int:
    """Run the minimal interactive CLI for the novel workflow."""
    reader = input if input_func is None else input_func

    try:
        workflow_inputs = collect_workflow_inputs(reader)
        result = run_basic_workflow(**workflow_inputs)
        print_workflow_result(result)
        persist_result(result)
    except Exception as exc:
        return handle_run_error(exc)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
