from __future__ import annotations

import json
import sys
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

    volume_no = normalized_volume_info.get("volume_no")
    response_text = LLMClient().generate_text_with_context(
        prompt,
        stage_name="chapter planning",
        volume_no=volume_no if isinstance(volume_no, int) else None,
    )
    chapter_plan = _parse_chapter_plan_json(response_text)
    _validate_required_fields(chapter_plan)
    _validate_beats(chapter_plan)
    return chapter_plan


def generate_volume_chapters(
    outline: dict[str, Any],
    volume_info: dict[str, Any],
    start_chapter_no: int,
) -> list[dict[str, Any]]:
    """Generate a list of chapter plans for one volume with a single LLM request."""
    if not isinstance(volume_info, dict):
        raise ChapterServiceError("volume_info must be a dictionary.")

    volume_no = volume_info.get("volume_no")
    if not isinstance(volume_no, int):
        raise ChapterServiceError("volume_info must contain an integer 'volume_no'.")

    chapter_count = _extract_planned_chapter_count(volume_info)
    prompt_template = load_prompt("volume_chapters.txt")
    prompt = (
        prompt_template.replace(
            "{outline}",
            json.dumps(outline, ensure_ascii=False, indent=2),
        )
        .replace(
            "{volume_info}",
            json.dumps(volume_info, ensure_ascii=False, indent=2),
        )
        .replace("{start_chapter_no}", str(start_chapter_no))
        .replace("{chapter_count}", str(chapter_count))
    )

    response_text = LLMClient().generate_text_with_context(
        prompt,
        stage_name="volume chapter planning",
        volume_no=volume_no,
    )
    chapter_plans = _parse_volume_chapter_plans_json(response_text, chapter_count)
    return _normalize_volume_chapter_plans(
        chapter_plans=chapter_plans,
        volume_no=volume_no,
        start_chapter_no=start_chapter_no,
    )


def _parse_chapter_plan_json(response_text: str) -> dict[str, Any]:
    return parse_json_object(response_text, ChapterParseError, "Chapter plan")


def _parse_volume_chapter_plans_json(
    response_text: str,
    expected_count: int,
) -> list[dict[str, Any]]:
    candidate = _extract_first_json_array_text(response_text)

    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError as exc:
        snippet = _build_response_snippet(response_text)
        print(
            "[LLM] stage=volume chapter planning status=parse_failure "
            f"response_snippet={snippet}",
            file=sys.stderr,
        )
        raise ChapterParseError(
            "Volume chapter plan response is not valid JSON: "
            f"{exc.msg} | response_snippet={snippet}"
        ) from exc

    if not isinstance(parsed, list):
        raise ChapterParseError("Volume chapter plan response must be a JSON array.")

    if not all(isinstance(item, dict) for item in parsed):
        raise ChapterParseError("Each volume chapter plan entry must be a JSON object.")

    if len(parsed) != expected_count:
        raise ChapterParseError(
            "Volume chapter plan response must contain exactly "
            f"{expected_count} chapter plan(s)."
        )

    return parsed


def _extract_first_json_array_text(response_text: str) -> str:
    decoder = json.JSONDecoder()
    normalized = response_text.strip()

    for start_index, char in enumerate(normalized):
        if char != "[":
            continue

        try:
            parsed, end_index = decoder.raw_decode(normalized[start_index:])
        except json.JSONDecodeError:
            continue

        if isinstance(parsed, list):
            return normalized[start_index : start_index + end_index]

    return normalized


def _build_response_snippet(response_text: str, max_chars: int = 200) -> str:
    collapsed = " ".join(response_text.strip().split())
    if len(collapsed) <= max_chars:
        return repr(collapsed)
    return repr(collapsed[:max_chars] + "...")


def _normalize_volume_chapter_plans(
    chapter_plans: list[dict[str, Any]],
    volume_no: int,
    start_chapter_no: int,
) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []

    for index, chapter_plan in enumerate(chapter_plans):
        _validate_required_fields(chapter_plan)
        _validate_beats(chapter_plan)
        normalized.append(
            {
                **chapter_plan,
                "chapter_no": start_chapter_no + index,
                "volume_no": volume_no,
                "status": "planned",
            }
        )

    return normalized


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
