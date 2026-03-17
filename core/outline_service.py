from __future__ import annotations

from typing import Any

from core.errors import OutlineGenerationError, collect_missing_fields, parse_json_object
from core.llm_client import LLMClient
from core.prompt_loader import load_prompt


REQUIRED_FIELDS: tuple[str, ...] = (
    "title",
    "core_hook",
    "theme",
    "protagonist",
    "conflict",
    "volume_plan",
)


class OutlineServiceError(OutlineGenerationError):
    """Base exception for outline generation failures."""


class OutlineParseError(OutlineServiceError):
    """Raised when the LLM response cannot be parsed into a valid outline."""


def generate_outline(topic: str, style: str, target: str) -> dict[str, Any]:
    """Generate a novel outline from the configured prompt template."""
    prompt_template = load_prompt("outline.txt")
    prompt = (
        prompt_template.replace("{topic}", topic)
        .replace("{style}", style)
        .replace("{target}", target)
    )

    response_text = LLMClient().generate_text(prompt)
    outline = _parse_outline_json(response_text)
    _validate_required_fields(outline)
    return outline


def _parse_outline_json(response_text: str) -> dict[str, Any]:
    return parse_json_object(response_text, OutlineParseError, "Outline")


def _validate_required_fields(outline: dict[str, Any]) -> None:
    missing_fields = collect_missing_fields(outline, REQUIRED_FIELDS)
    if missing_fields:
        missing = ", ".join(missing_fields)
        raise OutlineParseError(f"Outline response is missing required field(s): {missing}")
