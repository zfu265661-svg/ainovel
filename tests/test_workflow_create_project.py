from __future__ import annotations

from pathlib import Path

from core.storage import load_json
from core.workflow_service import create_project


def test_create_project_creates_project_shell(tmp_path: Path) -> None:
    project_root = tmp_path / "phase1-project"

    result = create_project(
        project_root=str(project_root),
        title="Phase 1 Novel",
        topic="xianxia",
        style="cold",
        target="serial",
    )

    assert result == {
        "project_id": "phase1-project",
        "title": "Phase 1 Novel",
        "topic": "xianxia",
        "style": "cold",
        "target": "serial",
        "current_chapter_no": 1,
        "status": "created",
    }
    assert load_json(str(project_root / "project.json")) == result
    assert load_json(str(project_root / "story_bible.json")) == {
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
    assert load_json(str(project_root / "chapters.json")) == {"chapters": []}
    assert load_json(str(project_root / "characters.json")) == {"characters": []}
    assert load_json(str(project_root / "timeline.json")) == {"events": []}
    assert load_json(str(project_root / "foreshadow.json")) == {"items": []}
    assert load_json(str(project_root / "plot_threads.json")) == {"threads": []}
    assert load_json(str(project_root / "locations.json")) == {"locations": []}
    assert load_json(str(project_root / "organizations.json")) == {"organizations": []}
    assert load_json(str(project_root / "style_guide.json")) == {
        "version": 1,
        "voice": "",
        "pacing": "",
        "tone": "",
        "forbidden_patterns": [],
        "notes": [],
    }
    assert load_json(str(project_root / "scenes.json")) == {"scenes": []}
    assert (project_root / "docs").is_dir()
    assert (project_root / "suggestions").is_dir()
    assert (project_root / "exports").is_dir()
