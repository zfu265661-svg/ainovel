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
    volume_info: dict[str, Any] | int | None = None,
    chapter_no: int | str = 1,
    previous_summary: str = "",
) -> dict[str, Any]:
    """Generate a chapter plan from the configured prompt template."""
    normalized_volume_info, normalized_chapter_no, normalized_previous_summary = (
        _normalize_generate_chapter_plan_inputs(
            volume_info=volume_info,
            chapter_no=chapter_no,
            previous_summary=previous_summary,
        )
    )

    prompt_template = load_prompt("chapter_plan.txt")
    prompt = (
        prompt_template.replace(
            "{outline}",
            json.dumps(outline, ensure_ascii=False, indent=2),
        )
        .replace(
            "{volume_info}",
            json.dumps(normalized_volume_info, ensure_ascii=False, indent=2),
        )
        .replace("{chapter_no}", str(normalized_chapter_no))
        .replace("{previous_summary}", normalized_previous_summary)
    )

    response_text = LLMClient().generate_text(prompt)
    chapter_plan = _parse_chapter_plan_json(response_text)
    _validate_required_fields(chapter_plan)
    _validate_beats(chapter_plan)
    return chapter_plan


def generate_volume_chapters(
    outline: dict[str, Any],
    volume_info: dict[str, Any],
    start_chapter_no: int,
) -> list[dict[str, Any]]:
    """Generate a list of chapter plans for one volume."""
    if not isinstance(volume_info, dict):
        raise ChapterServiceError("volume_info must be a dictionary.")

    volume_no = volume_info.get("volume_no")
    if not isinstance(volume_no, int):
        raise ChapterServiceError("volume_info must contain an integer 'volume_no'.")

    chapter_count = _extract_planned_chapter_count(volume_info)
    chapter_plans: list[dict[str, Any]] = []

    for offset in range(chapter_count):
        current_chapter_no = start_chapter_no + offset
        chapter_plan = generate_chapter_plan(
            outline=outline,
            volume_info=volume_info,
            chapter_no=current_chapter_no,
            previous_summary="",
        )
        chapter_plans.append(
            {
                **chapter_plan,
                "volume_no": volume_no,
                "status": "planned",
            }
        )

    return chapter_plans


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


def _normalize_generate_chapter_plan_inputs(
    volume_info: dict[str, Any] | int | None,
    chapter_no: int | str,
    previous_summary: str,
) -> tuple[dict[str, Any], int, str]:
    if isinstance(volume_info, int):
        normalized_chapter_no = volume_info
        if not isinstance(chapter_no, str):
            raise ChapterServiceError(
                "Legacy generate_chapter_plan call must pass previous_summary as a string."
            )
        return {}, normalized_chapter_no, chapter_no

    if not isinstance(chapter_no, int):
        raise ChapterServiceError("chapter_no must be an integer.")

    if volume_info is None:
        return {}, chapter_no, previous_summary

    return volume_info, chapter_no, previous_summary


def _extract_planned_chapter_count(volume_info: dict[str, Any]) -> int:
    planned_chapters = volume_info.get("planned_chapters")
    if isinstance(planned_chapters, int) and planned_chapters > 0:
        return planned_chapters

    if isinstance(planned_chapters, list) and planned_chapters:
        return len(planned_chapters)

    chapter_count = volume_info.get("chapter_count")
    if isinstance(chapter_count, int) and chapter_count > 0:
        return chapter_count

    raise ChapterServiceError(
        "volume_info must contain a positive 'planned_chapters' or 'chapter_count'."
    )
