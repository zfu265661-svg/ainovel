from __future__ import annotations

import json
from typing import Any

from core.errors import NovelAgentError, collect_missing_fields
from core.llm_client import LLMClient
from core.prompt_loader import load_prompt


REQUIRED_FIELDS: tuple[str, ...] = (
    "volume_no",
    "title",
    "goal",
    "core_conflict",
)
MAX_PHASE1_CHAPTERS_PER_VOLUME = 5


class VolumeServiceError(NovelAgentError):
    """Base exception for volume planning failures."""


class VolumeParseError(VolumeServiceError):
    """Raised when the LLM response cannot be parsed into a valid volume plan."""


def generate_volume_plan(outline: dict[str, Any]) -> list[dict[str, Any]]:
    """Generate a volume plan from the configured prompt template."""
    prompt_template = load_prompt("volume_plan.txt")
    prompt = prompt_template.replace(
        "{outline}",
        json.dumps(outline, ensure_ascii=False, indent=2),
    )

    response_text = LLMClient().generate_text_with_context(
        prompt,
        stage_name="volume plan generation",
    )
    if not response_text.strip():
        raise VolumeParseError("Volume plan response is empty.")

    volume_plan = _parse_volume_plan_json(response_text)
    _validate_volume_plan(volume_plan)
    return _normalize_volume_plan(volume_plan)


def _parse_volume_plan_json(response_text: str) -> list[dict[str, Any]]:
    try:
        parsed = json.loads(response_text)
    except json.JSONDecodeError as exc:
        raise VolumeParseError(
            f"Volume plan response is not valid JSON: {exc.msg}"
        ) from exc

    if not isinstance(parsed, list):
        raise VolumeParseError("Volume plan response must be a JSON array.")

    if not all(isinstance(item, dict) for item in parsed):
        raise VolumeParseError("Each volume plan entry must be a JSON object.")

    return parsed


def _validate_volume_plan(volume_plan: list[dict[str, Any]]) -> None:
    for index, volume in enumerate(volume_plan, start=1):
        missing_fields = collect_missing_fields(volume, REQUIRED_FIELDS)
        if missing_fields:
            missing = ", ".join(missing_fields)
            raise VolumeParseError(
                f"Volume plan entry {index} is missing required field(s): {missing}"
            )

        if not _has_valid_chapter_count(volume):
            raise VolumeParseError(
                "Volume plan entry "
                f"{index} must contain a positive 'planned_chapters' or 'chapter_count'."
            )


def _has_valid_chapter_count(volume: dict[str, Any]) -> bool:
    planned_chapters = volume.get("planned_chapters")
    if isinstance(planned_chapters, int) and planned_chapters > 0:
        return True

    chapter_count = volume.get("chapter_count")
    if isinstance(chapter_count, int) and chapter_count > 0:
        return True

    return False


def _normalize_volume_plan(volume_plan: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []

    for volume in volume_plan:
        normalized_volume = dict(volume)
        planned_chapters = normalized_volume.get("planned_chapters")
        if isinstance(planned_chapters, int) and planned_chapters > MAX_PHASE1_CHAPTERS_PER_VOLUME:
            normalized_volume["planned_chapters"] = MAX_PHASE1_CHAPTERS_PER_VOLUME
        elif isinstance(planned_chapters, list) and len(planned_chapters) > MAX_PHASE1_CHAPTERS_PER_VOLUME:
            normalized_volume["planned_chapters"] = planned_chapters[:MAX_PHASE1_CHAPTERS_PER_VOLUME]

        chapter_count = normalized_volume.get("chapter_count")
        if isinstance(chapter_count, int) and chapter_count > MAX_PHASE1_CHAPTERS_PER_VOLUME:
            normalized_volume["chapter_count"] = MAX_PHASE1_CHAPTERS_PER_VOLUME

        normalized.append(normalized_volume)

    return normalized
