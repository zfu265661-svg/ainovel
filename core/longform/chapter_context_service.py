from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable, cast


MAX_CONTEXT_TIMELINE_EVENTS = 5
MAX_CONTEXT_CHARACTERS = 8
MAX_CONTEXT_FORESHADOW_ITEMS = 8
MAX_CONTEXT_PLOT_THREADS = 6
MAX_CONTEXT_LOCATIONS = 6
MAX_CONTEXT_ORGANIZATIONS = 6
MAX_CONTEXT_SCENES = 8


def build_chapter_context(
    chapter_no: int,
    outline: dict[str, Any],
    previous_summary: str,
    characters: list[Any],
    timeline: list[Any],
    foreshadow: list[Any],
    chapter_plan: dict[str, Any] | None = None,
    story_bible: dict[str, Any] | None = None,
    plot_threads: dict[str, Any] | list[Any] | None = None,
    locations: dict[str, Any] | list[Any] | None = None,
    organizations: dict[str, Any] | list[Any] | None = None,
    style_guide: dict[str, Any] | None = None,
    scenes: dict[str, Any] | list[Any] | None = None,
) -> dict[str, Any]:
    """Build the stable context package used for chapter drafting."""
    task_text = _build_task_text(outline=outline, chapter_plan=chapter_plan)
    selected_characters, character_audit = _compact_character_context(
        characters,
        chapter_no=chapter_no,
        task_text=task_text,
    )
    selected_timeline = _select_recent_timeline_events(timeline, chapter_no)
    selected_foreshadow = _select_active_foreshadow_items(foreshadow)
    selected_plot_threads, plot_thread_audit = _select_context_items(
        _extract_items(plot_threads, "threads"),
        chapter_no=chapter_no,
        task_text=task_text,
        max_items=MAX_CONTEXT_PLOT_THREADS,
        allowed_fields=(
            "id",
            "title",
            "name",
            "summary",
            "status",
            "current_state",
            "related_characters",
            "related_locations",
            "planned_payoff",
        ),
        active_statuses=("active", "open", "planned"),
        fallback_to_first=False,
    )
    selected_locations, location_audit = _select_context_items(
        _extract_items(locations, "locations"),
        chapter_no=chapter_no,
        task_text=task_text,
        max_items=MAX_CONTEXT_LOCATIONS,
        allowed_fields=(
            "id",
            "name",
            "aliases",
            "description",
            "current_state",
            "rules",
            "related_characters",
            "related_organizations",
            "appearance_chapters",
            "status",
        ),
        active_statuses=("active", "open", "planned", "current"),
        fallback_to_first=False,
    )
    selected_organizations, organization_audit = _select_context_items(
        _extract_items(organizations, "organizations"),
        chapter_no=chapter_no,
        task_text=task_text,
        max_items=MAX_CONTEXT_ORGANIZATIONS,
        allowed_fields=(
            "id",
            "name",
            "aliases",
            "description",
            "goals",
            "members",
            "relationships",
            "appearance_chapters",
            "status",
        ),
        active_statuses=("active", "open", "planned", "current"),
        fallback_to_first=False,
    )
    selected_scenes, scene_audit = _select_context_items(
        _extract_items(scenes, "scenes"),
        chapter_no=chapter_no,
        task_text=task_text,
        max_items=MAX_CONTEXT_SCENES,
        allowed_fields=(
            "id",
            "chapter_no",
            "title",
            "goal",
            "summary",
            "status",
        ),
        active_statuses=("planned", "drafted", "rewritten", "active"),
        fallback_to_first=False,
    )

    return {
        "outline": outline,
        "previous_summary": _normalize_previous_summary(previous_summary),
        "characters": selected_characters,
        "timeline": selected_timeline,
        "foreshadow": selected_foreshadow,
        "story_bible": _compact_story_bible(story_bible),
        "plot_threads": selected_plot_threads,
        "locations": selected_locations,
        "organizations": selected_organizations,
        "style_guide": deepcopy(style_guide) if isinstance(style_guide, dict) else {},
        "scenes": selected_scenes,
        "context_audit": {
            "chapter_no": chapter_no,
            "selection_basis": "chapter_plan_and_outline_text" if task_text else "legacy_inputs",
            "limits": {
                "timeline": MAX_CONTEXT_TIMELINE_EVENTS,
                "characters": MAX_CONTEXT_CHARACTERS,
                "foreshadow": MAX_CONTEXT_FORESHADOW_ITEMS,
                "plot_threads": MAX_CONTEXT_PLOT_THREADS,
                "locations": MAX_CONTEXT_LOCATIONS,
                "organizations": MAX_CONTEXT_ORGANIZATIONS,
                "scenes": MAX_CONTEXT_SCENES,
            },
            "selected": {
                "outline": "included",
                "previous_summary": "included" if previous_summary else "empty",
                "characters": character_audit,
                "timeline": f"last {len(selected_timeline)} historical event(s)",
                "foreshadow": f"{len(selected_foreshadow)} open item(s)",
                "story_bible": "included" if isinstance(story_bible, dict) else "default_empty",
                "plot_threads": plot_thread_audit,
                "locations": location_audit,
                "organizations": organization_audit,
                "style_guide": "included" if isinstance(style_guide, dict) else "default_empty",
                "scenes": scene_audit,
            },
        },
    }


def _normalize_previous_summary(previous_summary: Any) -> str:
    if previous_summary is None:
        return ""
    return str(previous_summary)


def _compact_character_context(
    characters: list[Any],
    chapter_no: int,
    task_text: str,
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    compacted: list[tuple[dict[str, Any], str]] = []
    fallback: list[dict[str, Any]] = []

    for item in characters:
        if not isinstance(item, dict):
            continue

        name = str(item.get("name", "")).strip()
        if not name:
            continue

        traits = item.get("traits", [])
        compact_character = {
            "name": name,
            "role": str(item.get("role", "")).strip(),
            "traits": traits if isinstance(traits, list) else [],
            "current_state": str(item.get("current_state", "")).strip(),
        }
        fallback.append(compact_character)

        reason = _selection_reason(item, chapter_no, task_text)
        if reason is not None or not task_text:
            compacted.append((compact_character, reason or "legacy_valid_character"))

    if not compacted and fallback:
        compacted = [
            (item, "fallback_existing_character")
            for item in fallback[:MAX_CONTEXT_CHARACTERS]
        ]

    selected = compacted[:MAX_CONTEXT_CHARACTERS]
    return [item for item, _reason in selected], [
        {"name": str(item.get("name", "")), "reason": reason}
        for item, reason in selected
    ]



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
    ][:MAX_CONTEXT_FORESHADOW_ITEMS]


def _compact_story_bible(story_bible: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(story_bible, dict):
        return {}

    allowed_fields = (
        "version",
        "world",
        "era_background",
        "core_settings",
        "rules",
        "main_plot",
        "subplots",
        "foreshadowing",
        "conflicts",
        "themes",
        "style_guide",
        "taboos_and_limits",
    )
    return _compact_mapping(story_bible, allowed_fields)


def _select_context_items(
    items: list[Any],
    chapter_no: int,
    task_text: str,
    max_items: int,
    allowed_fields: Iterable[str],
    active_statuses: tuple[str, ...],
    fallback_to_first: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    selected: list[tuple[dict[str, Any], str]] = []
    valid_items: list[dict[str, Any]] = []

    for item in items:
        if not isinstance(item, dict):
            continue

        valid_items.append(item)
        reason = _selection_reason(item, chapter_no, task_text)
        status = str(item.get("status", "")).strip().lower()
        if reason is None and status in active_statuses:
            reason = "active_status"

        if reason is None:
            continue

        selected.append((_compact_mapping(item, allowed_fields), reason))

    if not selected and fallback_to_first:
        selected = [
            (_compact_mapping(item, allowed_fields), "fallback_existing_item")
            for item in valid_items[:max_items]
        ]

    selected.sort(key=lambda item: _selection_priority(item[1]))
    selected = selected[:max_items]
    return [item for item, _reason in selected], [
        {
            "id": _item_label(item),
            "reason": reason,
        }
        for item, reason in selected
    ]


def _selection_priority(reason: str) -> int:
    priorities = {
        "chapter_reference": 0,
        "task_reference": 1,
        "active_status": 2,
        "fallback_existing_item": 3,
    }
    return priorities.get(reason, 99)


def _extract_items(container: dict[str, Any] | list[Any] | None, key: str) -> list[Any]:
    if isinstance(container, list):
        return container
    if isinstance(container, dict):
        items = container.get(key)
        if isinstance(items, list):
            return items
    return []


def _selection_reason(
    item: dict[str, Any],
    chapter_no: int,
    task_text: str,
) -> str | None:
    if _item_mentions_chapter(item, chapter_no):
        return "chapter_reference"
    if task_text and _item_mentions_task(item, task_text):
        return "task_reference"
    return None


def _item_mentions_chapter(item: dict[str, Any], chapter_no: int) -> bool:
    direct_chapter_no = item.get("chapter_no")
    if direct_chapter_no == chapter_no:
        return True

    for field_name in (
        "chapters",
        "appearance_chapters",
        "appears_in_chapters",
        "related_chapters",
    ):
        if _chapter_list_contains(item.get(field_name), chapter_no):
            return True

    return False


def _chapter_list_contains(value: Any, chapter_no: int) -> bool:
    if not isinstance(value, list):
        return False

    chapter_tokens = {
        str(chapter_no),
        f"chapter_{chapter_no}",
        f"ch{chapter_no:03d}",
    }
    for item in value:
        if item == chapter_no:
            return True
        if str(item).strip().lower() in chapter_tokens:
            return True
    return False


def _item_mentions_task(item: dict[str, Any], task_text: str) -> bool:
    for candidate in _iter_item_labels(item):
        normalized = candidate.strip().lower()
        if normalized and normalized in task_text:
            return True
    return False


def _iter_item_labels(item: dict[str, Any]) -> Iterable[str]:
    for field_name in ("name", "title", "id", "target"):
        value = item.get(field_name)
        if isinstance(value, str):
            yield value

    aliases = item.get("aliases")
    if isinstance(aliases, list):
        for alias in aliases:
            if isinstance(alias, str):
                yield alias


def _item_label(item: dict[str, Any]) -> str:
    for value in _iter_item_labels(item):
        if value.strip():
            return value.strip()
    return "unknown"


def _compact_mapping(
    item: dict[str, Any],
    allowed_fields: Iterable[str],
) -> dict[str, Any]:
    return {
        field_name: deepcopy(item[field_name])
        for field_name in allowed_fields
        if field_name in item
    }


def _build_task_text(
    outline: dict[str, Any],
    chapter_plan: dict[str, Any] | None,
) -> str:
    if chapter_plan is None:
        return ""

    parts: list[str] = []
    _collect_strings(chapter_plan, parts)
    _collect_strings(
        {
            "title": outline.get("title"),
            "theme": outline.get("theme"),
            "core_hook": outline.get("core_hook"),
        },
        parts,
    )
    return "\n".join(parts).lower()


def _collect_strings(value: Any, parts: list[str]) -> None:
    if isinstance(value, str):
        stripped = value.strip()
        if stripped:
            parts.append(stripped)
        return

    if isinstance(value, dict):
        for nested in value.values():
            _collect_strings(nested, parts)
        return

    if isinstance(value, list):
        for item in value:
            _collect_strings(item, parts)
