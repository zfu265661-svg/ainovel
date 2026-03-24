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
    assert load_json(str(project_root / "chapters.json")) == {"chapters": []}
    assert load_json(str(project_root / "characters.json")) == {"characters": []}
    assert load_json(str(project_root / "timeline.json")) == {"events": []}
    assert load_json(str(project_root / "foreshadow.json")) == {"items": []}
    assert (project_root / "docs").is_dir()
    assert (project_root / "suggestions").is_dir()
