from __future__ import annotations

from pathlib import Path
from typing import Any

from core.errors import is_missing_required_value
from core.storage import load_json, save_json


TimelineEvent = dict[str, Any]
REQUIRED_FIELDS: tuple[str, ...] = ("id", "chapter_no", "event")
DEFAULT_PATH = "data/timeline.json"


class TimelineServiceError(RuntimeError):
    """Base exception for timeline management failures."""


class TimelineValidationError(TimelineServiceError):
    """Raised when timeline data is invalid."""


class TimelineConflictError(TimelineServiceError):
    """Raised when a timeline event conflicts with existing data."""


def load_timeline(path: str = DEFAULT_PATH) -> list[TimelineEvent]:
    """Load timeline events from a UTF-8 encoded JSON file."""
    resolved_path = _resolve_timeline_path(path)
    try:
        data = load_json(resolved_path)
    except FileNotFoundError:
        return []

    if not isinstance(data, list):
        raise TimelineValidationError(
            f"Timeline data file must contain a JSON array: {resolved_path}"
        )

    if not all(isinstance(item, dict) for item in data):
        raise TimelineValidationError(
            f"Each timeline event must be a JSON object: {resolved_path}"
        )

    return data


def save_timeline(
    events: list[TimelineEvent], path: str = DEFAULT_PATH
) -> None:
    """Validate and save timeline events to a UTF-8 encoded JSON file."""
    _validate_timeline_events(events)
    save_json(_resolve_timeline_path(path), events)


def add_timeline_event(
    event: TimelineEvent, path: str = DEFAULT_PATH
) -> None:
    """Add a validated timeline event, rejecting duplicate ids."""
    _validate_event(event)

    events = load_timeline(path)
    event_id = str(event["id"])
    if any(str(existing.get("id")) == event_id for existing in events):
        raise TimelineConflictError(
            f"Timeline event with id '{event['id']}' already exists."
        )

    events.append(event)
    save_timeline(events, path)


def get_events_by_chapter(
    chapter_no: int, path: str = DEFAULT_PATH
) -> list[TimelineEvent]:
    """Return timeline events whose chapter number matches exactly."""
    return [
        event
        for event in load_timeline(path)
        if event.get("chapter_no") == chapter_no
    ]


def _resolve_timeline_path(path: str) -> str:
    candidate = Path(path)
    if candidate.suffix.lower() == ".json":
        return str(candidate)
    return str(candidate / "timeline.json")


def _validate_timeline_events(events: list[TimelineEvent]) -> None:
    for event in events:
        _validate_event(event)

    seen_ids: set[str] = set()
    for event in events:
        event_id = str(event["id"])
        if event_id in seen_ids:
            raise TimelineConflictError(
                f"Timeline event with id '{event['id']}' already exists."
            )
        seen_ids.add(event_id)


def _validate_event(event: TimelineEvent) -> None:
    if not isinstance(event, dict):
        raise TimelineValidationError("Timeline event must be a dictionary.")

    missing_fields = [
        field for field in REQUIRED_FIELDS if is_missing_required_value(event, field)
    ]
    if missing_fields:
        missing = ", ".join(missing_fields)
        raise TimelineValidationError(
            f"Timeline event is missing required field(s): {missing}"
        )
