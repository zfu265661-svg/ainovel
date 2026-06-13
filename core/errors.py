"""Shared exception definitions for the novel agent."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from typing import Any, TypeVar


ErrorType = TypeVar("ErrorType", bound=Exception)


class NovelAgentError(Exception):
    """Base exception for all novel agent errors."""


class ConfigLoadError(NovelAgentError):
    """Raised when configuration loading fails."""


class PromptLoadError(NovelAgentError):
    """Raised when prompt loading fails."""


class LLMRequestError(NovelAgentError):
    """Raised when an LLM request fails."""


class OutlineGenerationError(NovelAgentError):
    """Raised when outline generation fails."""


class ChapterPlanError(NovelAgentError):
    """Raised when chapter planning fails."""


class DraftGenerationError(NovelAgentError):
    """Raised when draft generation fails."""


class ConsistencyCheckError(NovelAgentError):
    """Raised when a consistency check fails."""


class RewriteError(NovelAgentError):
    """Raised when rewriting content fails."""


class StorageError(NovelAgentError):
    """Raised when persistence or storage operations fail."""


def parse_json_object(
    response_text: str,
    error_type: type[ErrorType],
    response_name: str,
) -> dict[str, Any]:
    """Parse a JSON object and raise the provided error type on failure."""
    try:
        parsed = parse_json_with_repair(response_text)
    except ValueError as exc:
        raise error_type(f"{response_name} response is not valid JSON: {exc}") from exc

    if not isinstance(parsed, dict):
        raise error_type(f"{response_name} response must be a JSON object.")

    return parsed


def parse_json_array(
    response_text: str,
    error_type: type[ErrorType],
    response_name: str,
) -> list[Any]:
    """Parse a JSON array and raise the provided error type on failure."""
    try:
        parsed = parse_json_with_repair(response_text)
    except ValueError as exc:
        raise error_type(f"{response_name} response is not valid JSON: {exc}") from exc

    if not isinstance(parsed, list):
        raise error_type(f"{response_name} response must be a JSON array.")

    return parsed


def parse_json_with_repair(response_text: str) -> Any:
    """Parse JSON text with narrow formatting repairs after strict parsing fails."""
    attempts: list[str] = []
    errors: list[tuple[str, str, str]] = []

    parsed = _try_parse_json("strict", response_text, attempts, errors)
    if parsed["ok"]:
        return parsed["value"]

    sanitized = remove_invalid_control_chars(
        strip_markdown_fence(strip_bom(response_text).strip())
    )
    parsed = _try_parse_json("sanitized", sanitized, attempts, errors)
    if parsed["ok"]:
        return parsed["value"]

    extracted = extract_json_object_or_array(sanitized)
    if extracted is None:
        attempts.append("extracted")
        errors.append(("extracted", "ValueError", "No JSON object or array found"))
    else:
        parsed = _try_parse_json("extracted", extracted, attempts, errors)
        if parsed["ok"]:
            return parsed["value"]

    raise ValueError(_format_json_parse_failure(attempts, errors))


def parse_json_file_text(json_text: str) -> Any:
    """Parse stored JSON text strictly while tolerating a leading BOM."""
    try:
        return json.loads(strip_bom(json_text))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"strict parse failed; original_error={type(exc).__name__}: {exc.msg}"
        ) from exc
    except TypeError as exc:
        raise ValueError(
            f"strict parse failed; original_error={type(exc).__name__}: {exc}"
        ) from exc


def strip_bom(text: str) -> str:
    """Remove a leading UTF-8 BOM marker from decoded JSON text."""
    return text[1:] if text.startswith("\ufeff") else text


def strip_markdown_fence(text: str) -> str:
    """Remove a whole-response markdown code fence around JSON text."""
    stripped = text.strip()
    lines = stripped.splitlines()
    if len(lines) < 2:
        return stripped

    first_line = lines[0].strip().lower()
    last_line = lines[-1].strip()
    if first_line.startswith("```") and last_line == "```":
        return "\n".join(lines[1:-1]).strip()

    return stripped


def extract_json_object_or_array(text: str) -> str | None:
    """Return the first balanced JSON object or array substring, if present."""
    normalized = strip_bom(text).strip()
    for start_index, char in enumerate(normalized):
        if char not in "{[":
            continue
        end_index = _find_json_candidate_end(normalized, start_index)
        if end_index is not None:
            return normalized[start_index : end_index + 1]
    return None


def remove_invalid_control_chars(text: str) -> str:
    """Remove unescaped control characters inside JSON strings only."""
    result: list[str] = []
    in_string = False
    escaped = False

    for char in text:
        if in_string:
            if escaped:
                result.append(char)
                escaped = False
                continue
            if char == "\\":
                result.append(char)
                escaped = True
                continue
            if char == '"':
                result.append(char)
                in_string = False
                continue
            if ord(char) < 0x20:
                continue
            result.append(char)
            continue

        result.append(char)
        if char == '"':
            in_string = True

    return "".join(result)


def _try_parse_json(
    attempt_name: str,
    candidate: str,
    attempts: list[str],
    errors: list[tuple[str, str, str]],
) -> dict[str, Any]:
    attempts.append(attempt_name)
    try:
        return {"ok": True, "value": json.loads(candidate)}
    except json.JSONDecodeError as exc:
        errors.append((attempt_name, type(exc).__name__, exc.msg))
    except TypeError as exc:
        errors.append((attempt_name, type(exc).__name__, str(exc)))
    return {"ok": False, "value": None}


def _find_json_candidate_end(text: str, start_index: int) -> int | None:
    opening = text[start_index]
    expected_closer = "}" if opening == "{" else "]"
    stack = [expected_closer]
    in_string = False
    escaped = False

    for index in range(start_index + 1, len(text)):
        char = text[index]

        if in_string:
            if escaped:
                escaped = False
                continue
            if char == "\\":
                escaped = True
                continue
            if char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
            continue
        if char == "{":
            stack.append("}")
            continue
        if char == "[":
            stack.append("]")
            continue
        if char in "}]":
            if not stack or char != stack[-1]:
                return None
            stack.pop()
            if not stack:
                return index

    return None


def _format_json_parse_failure(
    attempts: list[str],
    errors: list[tuple[str, str, str]],
) -> str:
    original = errors[0] if errors else ("strict", "UnknownError", "unknown failure")
    final = errors[-1] if errors else original
    return (
        "parse failed after attempts="
        f"{attempts}; original_error={original[1]}: {original[2]}; "
        f"final_error={final[1]}: {final[2]}"
    )


def collect_missing_fields(
    data: Mapping[str, Any],
    required_fields: Iterable[str],
) -> list[str]:
    """Return required fields that are absent from the mapping."""
    return [field for field in required_fields if field not in data]


def is_missing_required_value(data: Mapping[str, Any], field: str) -> bool:
    """Return whether a required field is absent or contains blank text."""
    value = data.get(field)
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    return False
