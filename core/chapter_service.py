from __future__ import annotations

import json
from typing import Any

from core.errors import ChapterPlanError, collect_missing_fields, parse_json_object
from core.llm_client import LLMClient
from core.prompt_loader import load_prompt


REQUIRED_FIELDS: tuple[str, ...] = (
    "chapter_no",
    "title",
    "goal",
    "conflict",
    "beats",
    "ending_hook",
)


class ChapterServiceError(ChapterPlanError):
    """Base exception for chapter plan generation failures."""


class ChapterParseError(ChapterServiceError):
    """Raised when the LLM response cannot be parsed into a valid chapter plan."""


def generate_chapter_plan(
    outline: dict[str, Any],
    chapter_no: int,
    previous_summary: str,
) -> dict[str, Any]:
    """Generate a chapter plan from the configured prompt template."""
    prompt_template = load_prompt("chapter_plan.txt")
    prompt = (
        prompt_template.replace(
            "{outline}",
            json.dumps(outline, ensure_ascii=False, indent=2),
        )
        .replace("{chapter_no}", str(chapter_no))
        .replace("{previous_summary}", previous_summary)
    )

    response_text = LLMClient().generate_text(prompt)
    chapter_plan = _parse_chapter_plan_json(response_text)
    _validate_required_fields(chapter_plan)
    _validate_beats(chapter_plan)
    return chapter_plan


def _parse_chapter_plan_json(response_text: str) -> dict[str, Any]:
    return parse_json_object(response_text, ChapterParseError, "Chapter plan")


def _validate_required_fields(chapter_plan: dict[str, Any]) -> None:
    missing_fields = collect_missing_fields(chapter_plan, REQUIRED_FIELDS)
    if missing_fields:
        missing = ", ".join(missing_fields)
        raise ChapterParseError(
            f"Chapter plan response is missing required field(s): {missing}"
        )


def _validate_beats(chapter_plan: dict[str, Any]) -> None:
    beats = chapter_plan["beats"]
    if not isinstance(beats, list):
        raise ChapterParseError("Chapter plan field 'beats' must be a list.")
