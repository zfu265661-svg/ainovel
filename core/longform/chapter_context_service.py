from __future__ import annotations

from typing import Any, cast


MAX_CONTEXT_TIMELINE_EVENTS = 5


def build_chapter_context(
    chapter_no: int,
    outline: dict[str, Any],
    previous_summary: str,
    characters: list[Any],
    timeline: list[Any],
    foreshadow: list[Any],
) -> dict[str, Any]:
    """Build the stable context package used for chapter drafting."""
    return {
        "outline": outline,
        "previous_summary": _normalize_previous_summary(previous_summary),
        "characters": _compact_character_context(characters),
        "timeline": _select_recent_timeline_events(timeline, chapter_no),
        "foreshadow": _select_active_foreshadow_items(foreshadow),
    }


def _normalize_previous_summary(previous_summary: Any) -> str:
    if previous_summary is None:
        return ""
    return str(previous_summary)


def _compact_character_context(characters: list[Any]) -> list[dict[str, Any]]:
    compacted: list[dict[str, Any]] = []

    for item in characters:
        if not isinstance(item, dict):
            continue

        name = str(item.get("name", "")).strip()
        if not name:
            continue

        traits = item.get("traits", [])
        compacted.append(
            {
                "name": name,
                "role": str(item.get("role", "")).strip(),
                "traits": traits if isinstance(traits, list) else [],
                "current_state": str(item.get("current_state", "")).strip(),
            }
        )

    return compacted


def _select_recent_timeline_events(
    timeline: list[Any],
    chapter_no: int,
) -> list[dict[str, Any]]:
    historical_events = [
        cast(dict[str, Any], event)
        for event in timeline
        if isinstance(event, dict)
        and isinstance(event.get("chapter_no"), int)
        and cast(int, event["chapter_no"]) < chapter_no
    ]
    return historical_events[-MAX_CONTEXT_TIMELINE_EVENTS:]


def _select_active_foreshadow_items(foreshadow: list[Any]) -> list[dict[str, Any]]:
    return [
        cast(dict[str, Any], item)
        for item in foreshadow
        if isinstance(item, dict) and item.get("status") == "open"
    ]
