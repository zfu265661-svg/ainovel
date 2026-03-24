from __future__ import annotations

from pathlib import Path

import pytest

from core.storage import load_json, load_text, save_json, save_text
from core.workflow_service import commit_suggestion, create_project


def test_commit_suggestion_updates_formal_state_files(tmp_path: Path) -> None:
    project_root = tmp_path / "commit-project"
    create_project(
        project_root=str(project_root),
        title="Commit Novel",
        topic="xianxia",
        style="cold",
        target="serial",
    )

    save_json(
        str(project_root / "characters.json"),
        {"characters": [{"name": "Lin Yue", "role": "protagonist", "traits": [], "current_state": "alert"}]},
    )
    save_json(str(project_root / "timeline.json"), {"events": []})
    save_json(str(project_root / "foreshadow.json"), {"items": []})
    save_json(
        str(project_root / "suggestions" / "ch001.suggestion.json"),
        {
            "chapter_no": 1,
            "character_updates": [
                {"action": "update", "target": "Lin Yue", "content": "Became more cautious."},
                {"action": "add", "target": "Su He", "content": "A mentor appears."},
            ],
            "timeline_updates": [
                {"action": "add", "target": "chapter_1", "content": "The conflict begins."}
            ],
            "foreshadow_updates": [
                {"action": "add", "target": "fs-1", "content": "A clue is planted."},
                {"action": "update", "target": "fs-2", "content": "pending"},
            ],
            "notes": "Suggestion only.",
        },
    )
    save_text(str(project_root / "docs" / "ch001.plan.md"), "plan document should stay unchanged")
    original_plan = load_text(str(project_root / "docs" / "ch001.plan.md"))

    result = commit_suggestion(str(project_root), 1)

    assert result == {
        "chapter_no": 1,
        "suggestion_path": str(project_root / "suggestions" / "ch001.suggestion.json"),
        "characters_updated": 2,
        "timeline_updated": 1,
        "foreshadow_updated": 2,
    }
    assert load_json(str(project_root / "characters.json")) == {
        "characters": [
            {
                "name": "Lin Yue",
                "role": "protagonist",
                "traits": [],
                "current_state": "alert\nBecame more cautious.",
            },
            {
                "name": "Su He",
                "role": "unknown",
                "traits": [],
                "current_state": "A mentor appears.",
            },
        ]
    }
    assert load_json(str(project_root / "timeline.json")) == {
        "events": [
            {
                "chapter_no": 1,
                "event": "The conflict begins.",
                "action": "add",
                "target": "chapter_1",
            }
        ]
    }
    assert load_json(str(project_root / "foreshadow.json")) == {
        "items": [
            {
                "id": "fs-1",
                "content": "A clue is planted.",
                "introduced_in": "chapter_1",
                "status": "open",
            },
            {
                "id": "fs-2",
                "content": "pending",
                "introduced_in": "chapter_1",
                "status": "pending",
            },
        ]
    }
    suggestion = load_json(str(project_root / "suggestions" / "ch001.suggestion.json"))
    assert suggestion["committed"] is True
    assert suggestion["committed_chapter_no"] == 1
    assert load_text(str(project_root / "docs" / "ch001.plan.md")) == original_plan


def test_commit_suggestion_raises_when_suggestion_file_missing(tmp_path: Path) -> None:
    project_root = tmp_path / "commit-project"
    create_project(
        project_root=str(project_root),
        title="Commit Novel",
        topic="xianxia",
        style="cold",
        target="serial",
    )

    with pytest.raises(Exception, match="suggestion load|JSON file not found"):
        commit_suggestion(str(project_root), 1)


def test_commit_suggestion_raises_for_invalid_suggestion_structure(tmp_path: Path) -> None:
    project_root = tmp_path / "commit-project"
    create_project(
        project_root=str(project_root),
        title="Commit Novel",
        topic="xianxia",
        style="cold",
        target="serial",
    )
    save_json(
        str(project_root / "suggestions" / "ch001.suggestion.json"),
        {
            "chapter_no": 1,
            "character_updates": [],
            "timeline_updates": [],
            "notes": "missing foreshadow updates",
        },
    )

    with pytest.raises(Exception, match="missing required field\\(s\\): foreshadow_updates"):
        commit_suggestion(str(project_root), 1)


def test_commit_suggestion_rejects_duplicate_commit(tmp_path: Path) -> None:
    project_root = tmp_path / "commit-project"
    create_project(
        project_root=str(project_root),
        title="Commit Novel",
        topic="xianxia",
        style="cold",
        target="serial",
    )
    save_json(
        str(project_root / "suggestions" / "ch001.suggestion.json"),
        {
            "chapter_no": 1,
            "character_updates": [],
            "timeline_updates": [],
            "foreshadow_updates": [],
            "notes": "already committed",
            "committed": True,
            "committed_chapter_no": 1,
        },
    )

    with pytest.raises(Exception, match="already been committed"):
        commit_suggestion(str(project_root), 1)
