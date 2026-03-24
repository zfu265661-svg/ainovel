from __future__ import annotations

import json
from typing import Any

from core.errors import NovelAgentError, collect_missing_fields, parse_json_object
from core.llm_client import LLMClient
from core.prompt_loader import load_prompt


REQUIRED_FIELDS: tuple[str, ...] = (
    "chapter_no",
    "character_updates",
    "timeline_updates",
    "foreshadow_updates",
    "notes",
)
UPDATE_FIELDS: tuple[str, ...] = ("action", "target", "content")


class SuggestionServiceError(NovelAgentError):
    """Base exception for state suggestion generation failures."""


class SuggestionParseError(SuggestionServiceError):
    """Raised when the LLM response cannot be parsed into valid suggestions."""


def generate_state_suggestions(
    chapter_no: int,
    outline: dict[str, Any],
    chapter_plan: dict[str, Any],
    rewritten_text: str,
    chapter_summary: str,
    characters: list[Any],
    timeline: list[Any],
    foreshadow: list[Any],
) -> dict[str, Any]:
    """Generate structured state update suggestions for a chapter."""
    prompt_template = load_prompt("state_suggestion.txt")
    prompt = _build_prompt(
        prompt_template=prompt_template,
        chapter_no=chapter_no,
        outline=outline,
        chapter_plan=chapter_plan,
        rewritten_text=rewritten_text,
        chapter_summary=chapter_summary,
        characters=characters,
        timeline=timeline,
        foreshadow=foreshadow,
    )

    response_text = LLMClient().generate_text(prompt)
    if not response_text.strip():
        raise SuggestionParseError("State suggestion response is empty.")

    result = _parse_result_json(response_text)
    _validate_result(result)
    return result


def _build_prompt(
    prompt_template: str,
    chapter_no: int,
    outline: dict[str, Any],
    chapter_plan: dict[str, Any],
    rewritten_text: str,
    chapter_summary: str,
    characters: list[Any],
    timeline: list[Any],
    foreshadow: list[Any],
) -> str:
    return (
        prompt_template.replace("{chapter_no}", str(chapter_no))
        .replace("{outline}", json.dumps(outline, ensure_ascii=False, indent=2))
        .replace("{chapter_plan}", json.dumps(chapter_plan, ensure_ascii=False, indent=2))
        .replace("{rewritten_text}", rewritten_text)
        .replace("{chapter_summary}", chapter_summary)
        .replace("{characters}", json.dumps(characters, ensure_ascii=False, indent=2))
        .replace("{timeline}", json.dumps(timeline, ensure_ascii=False, indent=2))
        .replace("{foreshadow}", json.dumps(foreshadow, ensure_ascii=False, indent=2))
    )


def _parse_result_json(response_text: str) -> dict[str, Any]:
    return parse_json_object(
        response_text,
        SuggestionParseError,
        "State suggestion",
    )


def _validate_result(result: dict[str, Any]) -> None:
    missing_fields = collect_missing_fields(result, REQUIRED_FIELDS)
    if missing_fields:
        missing = ", ".join(missing_fields)
        raise SuggestionParseError(
            f"State suggestion response is missing required field(s): {missing}"
        )

    if not isinstance(result["chapter_no"], int):
        raise SuggestionParseError("State suggestion field 'chapter_no' must be an integer.")

    _validate_updates("character_updates", result["character_updates"])
    _validate_updates("timeline_updates", result["timeline_updates"])
    _validate_updates("foreshadow_updates", result["foreshadow_updates"])


def _validate_updates(field_name: str, updates: Any) -> None:
    if not isinstance(updates, list):
        raise SuggestionParseError(f"State suggestion field '{field_name}' must be a list.")

    for index, item in enumerate(updates, start=1):
        if not isinstance(item, dict):
            raise SuggestionParseError(
                f"State suggestion field '{field_name}' entry {index} must be a JSON object."
            )

        missing_fields = collect_missing_fields(item, UPDATE_FIELDS)
        if missing_fields:
            missing = ", ".join(missing_fields)
            raise SuggestionParseError(
                f"State suggestion field '{field_name}' entry {index} is missing required field(s): {missing}"
            )
