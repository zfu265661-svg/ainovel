from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from core.longform.chapter_context_service import build_chapter_context
from core.project_service import (
    get_chapter_plan_path,
    get_chapter_summary_path,
    get_project_file_paths,
)
from core.storage import load_json
from core.story_bible_service import load_agent_state
from core.workflow_service import (
    _find_chapter_entry,
    _load_chapter_index,
    _load_chapter_plan_from_project,
    _load_character_state,
    _load_foreshadow_state,
    _load_outline_from_project,
    _load_previous_summary,
    _load_timeline_state,
)


_ENHANCED_STATE_FILES: tuple[tuple[str, str, str | None], ...] = (
    ("story_bible", "story_bible_json", None),
    ("plot_threads", "plot_threads_json", "threads"),
    ("locations", "locations_json", "locations"),
    ("organizations", "organizations_json", "organizations"),
    ("style_guide", "style_guide_json", None),
    ("scenes", "scenes_json", "scenes"),
)
_THREAD_STATUS_GROUPS: dict[str, str] = {
    "active": "active",
    "current": "active",
    "open": "unresolved",
    "planned": "unresolved",
    "unresolved": "unresolved",
    "resolved": "resolved",
    "closed": "resolved",
    "dormant": "dormant",
    "paused": "dormant",
}


def build_context_inspection_report(project_root: str, chapter_no: int) -> dict[str, Any]:
    """Build the exact chapter context bundle and a compact inspect report."""
    paths = get_project_file_paths(project_root)
    outline = _load_outline_from_project(paths)
    chapters_index = _load_chapter_index(paths)
    chapter_entry = _find_chapter_entry(chapters_index, chapter_no)
    chapter_plan = _load_chapter_plan_from_project(project_root, chapter_no)
    previous_summary = _load_previous_summary(project_root, chapter_no)
    characters = _load_character_state(paths)
    timeline = _load_timeline_state(paths)
    foreshadow = _load_foreshadow_state(paths)
    agent_state = load_agent_state(project_root)

    context_bundle = build_chapter_context(
        chapter_no=chapter_no,
        outline=outline,
        previous_summary=previous_summary,
        characters=characters,
        timeline=timeline,
        foreshadow=foreshadow,
        chapter_plan=chapter_plan,
        story_bible=cast(dict[str, Any], agent_state["story_bible"]),
        plot_threads=agent_state["plot_threads"],
        locations=agent_state["locations"],
        organizations=agent_state["organizations"],
        style_guide=cast(dict[str, Any], agent_state["style_guide"]),
        scenes=agent_state["scenes"],
    )

    return {
        "project_root": project_root,
        "chapter_no": chapter_no,
        "chapter": chapter_entry,
        "context_audit": context_bundle["context_audit"],
        "selected_context_counts": _selected_context_counts(context_bundle),
        "selected_context_labels": _selected_context_labels(context_bundle),
        "selected_context": _selected_context_payload(context_bundle),
        "sources": _context_sources(project_root, chapter_no),
        "summary_chain": _summary_chain(project_root, chapter_no, previous_summary),
    }


def build_story_bible_inspection_report(project_root: str) -> dict[str, Any]:
    """Inspect Story Bible and enhanced state files without mutating state."""
    paths = get_project_file_paths(project_root)
    missing_files: list[str] = []
    corrupt_files: list[str] = []
    corrupt_file_errors: dict[str, str] = {}
    files: dict[str, dict[str, Any]] = {}
    counts: dict[str, int] = {}

    for state_name, path_key, item_key in _ENHANCED_STATE_FILES:
        path = Path(paths[path_key])
        if not path.is_file():
            missing_files.append(path.name)
            files[state_name] = {
                "path": str(path),
                "exists": False,
                "health": "missing_optional",
                "count": 0,
            }
            counts[state_name] = 0
            continue

        state = _safe_load_state_object(path)
        if state["error"] is not None:
            corrupt_files.append(path.name)
            corrupt_file_errors[path.name] = cast(str, state["error"])
            files[state_name] = {
                "path": str(path),
                "exists": True,
                "health": "corrupt",
                "count": 0,
            }
            counts[state_name] = 0
            continue

        data = cast(dict[str, Any], state["data"])
        count = _state_count(data, item_key)
        files[state_name] = {
            "path": str(path),
            "exists": True,
            "health": "healthy",
            "count": count,
        }
        counts[state_name] = count

    if corrupt_files:
        health = "corrupt"
    elif missing_files:
        health = "missing_optional"
    else:
        health = "healthy"

    return {
        "project_root": project_root,
        "enhanced_state_health": health,
        "missing_optional_files": missing_files,
        "corrupt_optional_files": corrupt_files,
        "corrupt_file_errors": corrupt_file_errors,
        "counts": counts,
        "files": files,
    }


def build_plot_threads_inspection_report(project_root: str) -> dict[str, Any]:
    """Inspect plot thread status and optional future graph fields."""
    paths = get_project_file_paths(project_root)
    path = Path(paths["plot_threads_json"])
    state = _safe_load_optional_state_object(path)
    health = state["health"]
    threads = _extract_items(state["data"], "threads")
    status_counts = _count_thread_statuses(threads)

    return {
        "project_root": project_root,
        "path": str(path),
        "health": health,
        "missing_optional_files": [path.name] if health == "missing_optional" else [],
        "corrupt_optional_files": [path.name] if health == "corrupt" else [],
        "corrupt_file_errors": {path.name: state["error"]} if state["error"] else {},
        "total": len(threads),
        "status_counts": status_counts,
        "type_counts": _count_thread_types(threads),
        "graph": _plot_thread_graph_stats(threads),
    }


def _selected_context_counts(context_bundle: dict[str, Any]) -> dict[str, int]:
    return {
        "characters": _len_if_list(context_bundle.get("characters")),
        "timeline": _len_if_list(context_bundle.get("timeline")),
        "foreshadow": _len_if_list(context_bundle.get("foreshadow")),
        "story_bible": _len_if_mapping(context_bundle.get("story_bible")),
        "plot_threads": _len_if_list(context_bundle.get("plot_threads")),
        "locations": _len_if_list(context_bundle.get("locations")),
        "organizations": _len_if_list(context_bundle.get("organizations")),
        "style_guide": _len_if_mapping(context_bundle.get("style_guide")),
        "scenes": _len_if_list(context_bundle.get("scenes")),
    }


def _selected_context_labels(context_bundle: dict[str, Any]) -> dict[str, list[str]]:
    return {
        "characters": _labels_from_items(context_bundle.get("characters")),
        "timeline": _labels_from_items(context_bundle.get("timeline")),
        "foreshadow": _labels_from_items(context_bundle.get("foreshadow")),
        "story_bible": list(cast(dict[str, Any], context_bundle.get("story_bible", {})).keys())
        if isinstance(context_bundle.get("story_bible"), dict)
        else [],
        "plot_threads": _labels_from_items(context_bundle.get("plot_threads")),
        "locations": _labels_from_items(context_bundle.get("locations")),
        "organizations": _labels_from_items(context_bundle.get("organizations")),
        "style_guide": list(cast(dict[str, Any], context_bundle.get("style_guide", {})).keys())
        if isinstance(context_bundle.get("style_guide"), dict)
        else [],
        "scenes": _labels_from_items(context_bundle.get("scenes")),
    }


def _selected_context_payload(context_bundle: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "characters",
        "timeline",
        "foreshadow",
        "story_bible",
        "plot_threads",
        "locations",
        "organizations",
        "style_guide",
        "scenes",
    )
    return {key: context_bundle.get(key) for key in keys}


def _context_sources(project_root: str, chapter_no: int) -> dict[str, Any]:
    paths = get_project_file_paths(project_root)
    previous_summary_path = (
        get_chapter_summary_path(project_root, chapter_no - 1)
        if chapter_no > 1
        else None
    )
    return {
        "outline_path": str(Path(paths["docs_dir"]) / "outline.md"),
        "chapter_plan_path": get_chapter_plan_path(project_root, chapter_no),
        "previous_summary_path": previous_summary_path,
        "formal_state_files": {
            "characters": paths["characters_json"],
            "timeline": paths["timeline_json"],
            "foreshadow": paths["foreshadow_json"],
        },
        "enhanced_state_files": {
            state_name: paths[path_key]
            for state_name, path_key, _item_key in _ENHANCED_STATE_FILES
        },
    }


def _summary_chain(
    project_root: str,
    chapter_no: int,
    previous_summary: str,
) -> dict[str, Any]:
    if chapter_no <= 1:
        return {
            "previous_summary": {
                "chapter_no": None,
                "path": None,
                "exists": False,
                "selected": False,
            }
        }

    path = get_chapter_summary_path(project_root, chapter_no - 1)
    exists = Path(path).is_file()
    return {
        "previous_summary": {
            "chapter_no": chapter_no - 1,
            "path": path,
            "exists": exists,
            "selected": bool(previous_summary),
        }
    }


def _safe_load_optional_state_object(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {
            "health": "missing_optional",
            "data": {"threads": []},
            "error": None,
        }

    state = _safe_load_state_object(path)
    if state["error"] is not None:
        return {
            "health": "corrupt",
            "data": {"threads": []},
            "error": state["error"],
        }

    return {
        "health": "healthy",
        "data": state["data"],
        "error": None,
    }


def _safe_load_state_object(path: Path) -> dict[str, Any]:
    try:
        data = load_json(str(path))
    except Exception as exc:
        return {"data": None, "error": str(exc)}

    if not isinstance(data, dict):
        return {
            "data": None,
            "error": f"Enhanced state file must contain a JSON object: {path}",
        }

    return {"data": data, "error": None}


def _state_count(data: dict[str, Any], item_key: str | None) -> int:
    if item_key is not None:
        items = data.get(item_key)
        return len(items) if isinstance(items, list) else 0

    return len([key for key, value in data.items() if _has_content(value)])


def _count_thread_statuses(threads: list[dict[str, Any]]) -> dict[str, int]:
    counts = {
        "active": 0,
        "unresolved": 0,
        "resolved": 0,
        "dormant": 0,
        "unknown": 0,
    }
    for thread in threads:
        raw_status = str(thread.get("status", "")).strip().lower()
        group = _THREAD_STATUS_GROUPS.get(raw_status, "unknown")
        counts[group] += 1
    return counts


def _count_thread_types(threads: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for thread in threads:
        thread_type = str(thread.get("type", "unknown")).strip().lower() or "unknown"
        counts[thread_type] = counts.get(thread_type, 0) + 1
    return counts


def _plot_thread_graph_stats(threads: list[dict[str, Any]]) -> dict[str, Any]:
    nodes = []
    for thread in threads:
        thread_nodes = thread.get("nodes")
        if isinstance(thread_nodes, list):
            nodes.extend(item for item in thread_nodes if isinstance(item, dict))

    graph_items = [*threads, *nodes]
    stats = {
        "graph_fields_present": False,
        "nodes": len(nodes),
        "depends_on_edges": sum(_count_refs(item.get("depends_on")) for item in graph_items),
        "unlocks_edges": sum(_count_refs(item.get("unlocks")) for item in graph_items),
        "converges_to_refs": sum(_count_refs(item.get("converges_to")) for item in graph_items),
        "branch_refs": sum(1 for item in graph_items if item.get("branch_id")),
        "merge_refs": sum(1 for item in graph_items if item.get("merge_target_id")),
    }
    stats["graph_fields_present"] = any(
        value for key, value in stats.items() if key != "graph_fields_present"
    )
    return stats


def _extract_items(container: Any, key: str) -> list[dict[str, Any]]:
    if not isinstance(container, dict):
        return []
    items = container.get(key)
    if not isinstance(items, list):
        return []
    return [cast(dict[str, Any], item) for item in items if isinstance(item, dict)]


def _labels_from_items(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    labels: list[str] = []
    for item in value:
        if isinstance(item, dict):
            labels.append(_item_label(item))
    return labels


def _item_label(item: dict[str, Any]) -> str:
    for key in ("name", "title", "id", "target", "event", "content", "goal"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    chapter_no = item.get("chapter_no")
    if isinstance(chapter_no, int):
        return f"chapter_{chapter_no}"
    return "unknown"


def _count_refs(value: Any) -> int:
    if isinstance(value, list):
        return len(value)
    if isinstance(value, str) and value.strip():
        return 1
    return 0


def _len_if_list(value: Any) -> int:
    return len(value) if isinstance(value, list) else 0


def _len_if_mapping(value: Any) -> int:
    return len(value) if isinstance(value, dict) else 0


def _has_content(value: Any) -> bool:
    if value in ("", None):
        return False
    if isinstance(value, (list, dict)):
        return bool(value)
    return True
