from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from core.project_service import get_project_file_paths
from core.storage import load_json


def load_agent_state(project_root: str) -> dict[str, Any]:
    """Load optional agent-kernel state with safe defaults for legacy projects."""
    return {
        "story_bible": load_story_bible(project_root),
        "plot_threads": load_plot_threads(project_root),
        "locations": load_locations(project_root),
        "organizations": load_organizations(project_root),
        "style_guide": load_style_guide(project_root),
        "scenes": load_scenes(project_root),
    }


def load_story_bible(project_root: str) -> dict[str, Any]:
    paths = get_project_file_paths(project_root)
    return _load_optional_object(
        paths["story_bible_json"],
        _default_story_bible(),
        "Story bible",
    )


def load_plot_threads(project_root: str) -> dict[str, Any]:
    paths = get_project_file_paths(project_root)
    return _load_optional_object(
        paths["plot_threads_json"],
        {"threads": []},
        "Plot threads",
    )


def load_locations(project_root: str) -> dict[str, Any]:
    paths = get_project_file_paths(project_root)
    return _load_optional_object(
        paths["locations_json"],
        {"locations": []},
        "Locations",
    )


def load_organizations(project_root: str) -> dict[str, Any]:
    paths = get_project_file_paths(project_root)
    return _load_optional_object(
        paths["organizations_json"],
        {"organizations": []},
        "Organizations",
    )


def load_style_guide(project_root: str) -> dict[str, Any]:
    paths = get_project_file_paths(project_root)
    return _load_optional_object(
        paths["style_guide_json"],
        _default_style_guide(),
        "Style guide",
    )


def load_scenes(project_root: str) -> dict[str, Any]:
    paths = get_project_file_paths(project_root)
    return _load_optional_object(
        paths["scenes_json"],
        {"scenes": []},
        "Scenes",
    )


def _load_optional_object(
    path: str,
    default_payload: dict[str, Any],
    label: str,
) -> dict[str, Any]:
    if not Path(path).is_file():
        return deepcopy(default_payload)

    data = load_json(path)
    if not isinstance(data, dict):
        raise ValueError(f"{label} file must contain a JSON object: {path}")

    return data


def _default_story_bible() -> dict[str, Any]:
    return {
        "version": 1,
        "world": {},
        "era_background": "",
        "core_settings": [],
        "rules": [],
        "organizations": [],
        "locations": [],
        "characters": [],
        "character_relationships": [],
        "main_plot": [],
        "subplots": [],
        "foreshadowing": [],
        "conflicts": [],
        "themes": [],
        "style_guide": {},
        "taboos_and_limits": [],
    }


def _default_style_guide() -> dict[str, Any]:
    return {
        "version": 1,
        "voice": "",
        "pacing": "",
        "tone": "",
        "forbidden_patterns": [],
        "notes": [],
    }
