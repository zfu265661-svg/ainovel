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
        parsed = json.loads(response_text)
    except json.JSONDecodeError as exc:
        raise error_type(f"{response_name} response is not valid JSON: {exc.msg}") from exc

    if not isinstance(parsed, dict):
        raise error_type(f"{response_name} response must be a JSON object.")

    return parsed


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
