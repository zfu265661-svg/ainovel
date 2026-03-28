from __future__ import annotations

import json
import re
import sys
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

    response_text = LLMClient().generate_text_with_context(
        prompt,
        stage_name="state suggestion generation",
    )
    if not response_text.strip():
        raise SuggestionParseError("State suggestion response is empty.")

    result = _parse_result_json(response_text)
    result = _normalize_result(result)
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
    candidate = _extract_first_json_object_text(response_text)

    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError as exc:
        snippet = _build_response_snippet(response_text)
        print(
            "[LLM] stage=state suggestion generation status=parse_failure "
            f"response_snippet={snippet}",
            file=sys.stderr,
        )
        raise SuggestionParseError(
            "State suggestion response is not valid JSON: "
            f"{exc.msg} | response_snippet={snippet}"
        ) from exc

    if not isinstance(parsed, dict):
        raise SuggestionParseError("State suggestion response must be a JSON object.")

    return parsed


def _normalize_result(result: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(result)

    if "character_updates" in normalized:
        normalized["character_updates"] = _normalize_character_updates(
            normalized["character_updates"]
        )
    if "timeline_updates" in normalized:
        normalized["timeline_updates"] = _normalize_timeline_updates(
            normalized["timeline_updates"]
        )
    if "foreshadow_updates" in normalized:
        normalized["foreshadow_updates"] = _normalize_foreshadow_updates(
            normalized["foreshadow_updates"]
        )

    return normalized


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


def _normalize_character_updates(updates: Any) -> Any:
    if not isinstance(updates, list):
        return updates

    normalized: list[dict[str, Any]] = []
    for item in updates:
        if not isinstance(item, dict):
            normalized.append(item)
            continue

        if all(field in item for field in UPDATE_FIELDS):
            normalized.append(item)
            continue

        character_name = item.get("character_name")
        update_fields = item.get("update_fields")
        if isinstance(character_name, str) and isinstance(update_fields, dict):
            normalized.append(
                {
                    "action": "update",
                    "target": character_name,
                    "content": _flatten_mapping(update_fields),
                }
            )
            continue

        normalized.append(item)

    return normalized


def _normalize_timeline_updates(updates: Any) -> Any:
    if not isinstance(updates, list):
        return updates

    normalized: list[dict[str, Any]] = []
    for item in updates:
        if not isinstance(item, dict):
            normalized.append(item)
            continue

        if all(field in item for field in UPDATE_FIELDS):
            normalized.append(item)
            continue

        event = item.get("event")
        description = item.get("description")
        if isinstance(event, str) and isinstance(description, str):
            impact = item.get("impact")
            content = description.strip()
            if isinstance(impact, str) and impact.strip():
                content = f"{content}\n影响: {impact.strip()}"
            normalized.append(
                {
                    "action": "add",
                    "target": event,
                    "content": content,
                }
            )
            continue

        normalized.append(item)

    return normalized


def _normalize_foreshadow_updates(updates: Any) -> Any:
    if not isinstance(updates, list):
        return updates

    normalized: list[dict[str, Any]] = []
    for item in updates:
        if not isinstance(item, dict):
            normalized.append(item)
            continue

        if all(field in item for field in UPDATE_FIELDS):
            normalized.append(item)
            continue

        foreshadow_content = item.get("foreshadow_content")
        details = item.get("details")
        if isinstance(foreshadow_content, str):
            content_parts = [foreshadow_content.strip()]
            if isinstance(details, str) and details.strip():
                content_parts.append(details.strip())
            normalized.append(
                {
                    "action": "add",
                    "target": _slugify_identifier(foreshadow_content),
                    "content": "\n".join(part for part in content_parts if part),
                }
            )
            continue

        normalized.append(item)

    return normalized


def _extract_first_json_object_text(response_text: str) -> str:
    decoder = json.JSONDecoder()
    normalized = response_text.strip()

    for start_index, char in enumerate(normalized):
        if char != "{":
            continue

        try:
            parsed, end_index = decoder.raw_decode(normalized[start_index:])
        except json.JSONDecodeError:
            continue

        if isinstance(parsed, dict):
            return normalized[start_index : start_index + end_index]

    return normalized


def _build_response_snippet(response_text: str, max_chars: int = 200) -> str:
    collapsed = " ".join(response_text.strip().split())
    if len(collapsed) <= max_chars:
        return repr(collapsed)
    return repr(collapsed[:max_chars] + "...")


def _flatten_mapping(data: dict[str, Any]) -> str:
    parts: list[str] = []
    for key, value in data.items():
        text = str(value).strip()
        if not text:
            continue
        parts.append(f"{key}: {text}")
    return "\n".join(parts)


def _slugify_identifier(value: str) -> str:
    collapsed = re.sub(r"\s+", "_", value.strip().lower())
    collapsed = re.sub(r"[^0-9a-zA-Z_\u4e00-\u9fff-]", "_", collapsed)
    collapsed = re.sub(r"_+", "_", collapsed).strip("_")
    return collapsed or "foreshadow_item"
