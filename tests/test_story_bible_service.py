from __future__ import annotations

from pathlib import Path

import pytest

from core.storage import save_json, save_text
from core.story_bible_service import (
    load_agent_state,
    load_locations,
    load_story_bible,
)


def test_load_story_bible_returns_default_for_legacy_project(tmp_path: Path) -> None:
    project_root = tmp_path / "legacy-project"
    project_root.mkdir()

    story_bible = load_story_bible(str(project_root))

    assert story_bible["version"] == 1
    assert story_bible["world"] == {}
    assert story_bible["main_plot"] == []


def test_load_agent_state_reads_enhanced_state_files(tmp_path: Path) -> None:
    project_root = tmp_path / "agent-project"
    project_root.mkdir()
    save_json(
        str(project_root / "story_bible.json"),
        {"version": 1, "world": {"name": "Mirror City"}},
    )
    save_json(
        str(project_root / "plot_threads.json"),
        {"threads": [{"id": "main", "status": "active"}]},
    )
    save_json(
        str(project_root / "locations.json"),
        {"locations": [{"name": "North Gate"}]},
    )
    save_json(
        str(project_root / "organizations.json"),
        {"organizations": [{"name": "Night Office"}]},
    )
    save_json(
        str(project_root / "style_guide.json"),
        {"version": 1, "voice": "restrained"},
    )
    save_json(
        str(project_root / "scenes.json"),
        {"scenes": [{"id": "ch001-sc001"}]},
    )

    state = load_agent_state(str(project_root))

    assert state["story_bible"]["world"]["name"] == "Mirror City"
    assert state["plot_threads"]["threads"][0]["id"] == "main"
    assert state["locations"]["locations"][0]["name"] == "North Gate"
    assert state["organizations"]["organizations"][0]["name"] == "Night Office"
    assert state["style_guide"]["voice"] == "restrained"
    assert state["scenes"]["scenes"][0]["id"] == "ch001-sc001"


def test_load_optional_state_rejects_non_object_json(tmp_path: Path) -> None:
    project_root = tmp_path / "agent-project"
    project_root.mkdir()
    save_text(str(project_root / "locations.json"), "[]")

    with pytest.raises(ValueError, match="Locations file must contain a JSON object"):
        load_locations(str(project_root))
