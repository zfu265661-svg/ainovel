from __future__ import annotations

import json
from typing import Any

from core.errors import (
    ConsistencyCheckError as SharedConsistencyCheckError,
    collect_missing_fields,
    parse_json_object,
)
from core.llm_client import LLMClient
from core.prompt_loader import load_prompt


REQUIRED_FIELDS: tuple[str, ...] = ("has_issue", "issues", "suggestions")


class ConsistencyCheckError(SharedConsistencyCheckError):
    """Base exception for consistency check failures."""


class ConsistencyCheckParseError(ConsistencyCheckError):
    """Raised when the LLM response cannot be parsed into a valid result."""


def check_consistency(
    draft_text: str,
    outline: dict[str, Any],
    character_info: dict[str, Any],
    timeline: list[Any],
) -> dict[str, Any]:
    """Run a consistency check on draft text and structured story context."""
    prompt_template = load_prompt("consistency_check.txt")
    prompt = _build_prompt(prompt_template, draft_text, outline, character_info, timeline)

    response_text = LLMClient().generate_text(prompt)
    result = _parse_result_json(response_text)
    _validate_result(result)
    return result


def _build_prompt(
    prompt_template: str,
    draft_text: str,
    outline: dict[str, Any],
    character_info: dict[str, Any],
    timeline: list[Any],
) -> str:
    serialized_outline = json.dumps(outline, ensure_ascii=False, indent=2)
    serialized_character_info = json.dumps(character_info, ensure_ascii=False, indent=2)
    serialized_timeline = json.dumps(timeline, ensure_ascii=False, indent=2)

    return (
        f"{prompt_template}\n\n"
        f"【正文】\n{draft_text}\n\n"
        f"【大纲】\n{serialized_outline}\n\n"
        f"【角色设定】\n{serialized_character_info}\n\n"
        f"【时间线】\n{serialized_timeline}\n"
    )


def _parse_result_json(response_text: str) -> dict[str, Any]:
    return parse_json_object(
        response_text,
        ConsistencyCheckParseError,
        "Consistency check",
    )


def _validate_result(result: dict[str, Any]) -> None:
    missing_fields = collect_missing_fields(result, REQUIRED_FIELDS)
    if missing_fields:
        missing = ", ".join(missing_fields)
        raise ConsistencyCheckParseError(
            f"Consistency check response is missing required field(s): {missing}"
        )

    if not isinstance(result["has_issue"], bool):
        raise ConsistencyCheckParseError("Consistency check field 'has_issue' must be a boolean.")

    if not isinstance(result["issues"], list):
        raise ConsistencyCheckParseError("Consistency check field 'issues' must be a list.")

    if not isinstance(result["suggestions"], list):
        raise ConsistencyCheckParseError(
            "Consistency check field 'suggestions' must be a list."
        )
