from __future__ import annotations

from pathlib import Path

import pytest

from core.longform.project_state_repository import (
    get_chapter_review_path,
    get_chapter_snapshot_path,
)
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
    review = load_json(get_chapter_review_path(str(project_root), 1))
    assert review["created_at"]
    assert review["suggestion_path"] == str(project_root / "suggestions" / "ch001.suggestion.json")
    assert review["approved_suggestion"]["chapter_no"] == 1
    assert review["approved_suggestion"]["notes"] == "Suggestion only."
    assert review["consistency_check"]["blockers"] == []
    assert review["consistency_check"]["warnings"] == []
    assert review["committed"] is True
    assert review["committed_chapter_no"] == 1
    assert not Path(get_chapter_snapshot_path(str(project_root), 1)).exists()
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


def test_commit_suggestion_keeps_review_uncommitted_when_state_commit_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "commit-project"
    create_project(
        project_root=str(project_root),
        title="Commit Novel",
        topic="xianxia",
        style="cold",
        target="serial",
    )
    save_json(str(project_root / "characters.json"), {"characters": []})
    save_json(str(project_root / "timeline.json"), {"events": []})
    save_json(str(project_root / "foreshadow.json"), {"items": []})
    save_json(
        str(project_root / "suggestions" / "ch001.suggestion.json"),
        {
            "chapter_no": 1,
            "character_updates": [],
            "timeline_updates": [
                {"action": "add", "target": "chapter_1", "content": "The conflict begins."}
            ],
            "foreshadow_updates": [],
            "notes": "Suggestion only.",
        },
    )

    original_save_json = save_json

    def failing_save_json(path: str, data) -> None:
        if path == str(project_root / "timeline.json"):
            raise RuntimeError("timeline write failed")
        original_save_json(path, data)

    monkeypatch.setattr("core.workflow_service.save_json", failing_save_json)

    with pytest.raises(Exception, match="timeline state persistence: timeline write failed"):
        commit_suggestion(str(project_root), 1)

    review = load_json(get_chapter_review_path(str(project_root), 1))
    suggestion = load_json(str(project_root / "suggestions" / "ch001.suggestion.json"))
    assert review["consistency_check"]["blockers"] == []
    assert review["committed"] is False
    assert review["committed_chapter_no"] is None
    assert "committed" not in suggestion
    assert "committed_chapter_no" not in suggestion


def test_commit_suggestion_restores_uncommitted_review_and_suggestion_when_marker_write_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "commit-project"
    create_project(
        project_root=str(project_root),
        title="Commit Novel",
        topic="xianxia",
        style="cold",
        target="serial",
    )
    save_json(str(project_root / "characters.json"), {"characters": []})
    save_json(str(project_root / "timeline.json"), {"events": []})
    save_json(str(project_root / "foreshadow.json"), {"items": []})
    suggestion_path = str(project_root / "suggestions" / "ch001.suggestion.json")
    review_path = get_chapter_review_path(str(project_root), 1)
    save_json(
        suggestion_path,
        {
            "chapter_no": 1,
            "character_updates": [],
            "timeline_updates": [],
            "foreshadow_updates": [],
            "notes": "Suggestion only.",
        },
    )

    original_save_json = save_json
    failed_once = {"value": False}

    def failing_save_json(path: str, data) -> None:
        if (
            path == suggestion_path
            and isinstance(data, dict)
            and data.get("committed") is True
            and not failed_once["value"]
        ):
            failed_once["value"] = True
            raise RuntimeError("suggestion marker write failed")
        original_save_json(path, data)

    monkeypatch.setattr("core.workflow_service.save_json", failing_save_json)

    with pytest.raises(Exception, match="suggestion marker write failed"):
        commit_suggestion(str(project_root), 1)

    review = load_json(review_path)
    suggestion = load_json(suggestion_path)
    assert review["consistency_check"]["blockers"] == []
    assert review["committed"] is False
    assert review["committed_chapter_no"] is None
    assert "committed" not in suggestion
    assert "committed_chapter_no" not in suggestion


def test_commit_suggestion_blocks_before_state_write_when_consistency_check_finds_blocker(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "commit-project"
    create_project(
        project_root=str(project_root),
        title="Commit Novel",
        topic="xianxia",
        style="cold",
        target="serial",
    )
    save_json(str(project_root / "characters.json"), {"characters": []})
    save_json(str(project_root / "timeline.json"), {"events": []})
    save_json(str(project_root / "foreshadow.json"), {"items": []})
    save_json(
        str(project_root / "suggestions" / "ch001.suggestion.json"),
        {
            "chapter_no": 1,
            "character_updates": [],
            "timeline_updates": [
                {"action": "add", "target": "chapter_1", "content": "   "}
            ],
            "foreshadow_updates": [],
            "notes": "Suggestion only.",
        },
    )

    with pytest.raises(Exception, match="contains blocker"):
        commit_suggestion(str(project_root), 1)

    review = load_json(get_chapter_review_path(str(project_root), 1))
    suggestion = load_json(str(project_root / "suggestions" / "ch001.suggestion.json"))
    assert review["committed"] is False
    assert review["committed_chapter_no"] is None
    assert review["consistency_check"]["blockers"] == [
        {
            "code": "blank_update_field",
            "message": "approved_suggestion.timeline_updates[0].content must be non-empty.",
            "field": "approved_suggestion.timeline_updates[0].content",
        }
    ]
    assert "committed" not in suggestion
    assert "committed_chapter_no" not in suggestion
    assert load_json(str(project_root / "characters.json")) == {"characters": []}
    assert load_json(str(project_root / "timeline.json")) == {"events": []}
    assert load_json(str(project_root / "foreshadow.json")) == {"items": []}


def test_commit_suggestion_allows_warning_only_review_and_preserves_warning_in_committed_review(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "commit-project"
    create_project(
        project_root=str(project_root),
        title="Commit Novel",
        topic="xianxia",
        style="cold",
        target="serial",
    )
    save_json(str(project_root / "characters.json"), {"characters": []})
    save_json(str(project_root / "timeline.json"), {"events": []})
    save_json(str(project_root / "foreshadow.json"), {"items": []})
    save_json(
        str(project_root / "suggestions" / "ch002.suggestion.json"),
        {
            "chapter_no": 2,
            "character_updates": [
                {"action": "update", "target": "Lin Yue", "content": "Becomes more cautious."}
            ],
            "timeline_updates": [],
            "foreshadow_updates": [],
            "notes": "Suggestion only.",
        },
    )

    result = commit_suggestion(str(project_root), 2)

    assert result == {
        "chapter_no": 2,
        "suggestion_path": str(project_root / "suggestions" / "ch002.suggestion.json"),
        "characters_updated": 1,
        "timeline_updated": 0,
        "foreshadow_updated": 0,
    }
    review = load_json(get_chapter_review_path(str(project_root), 2))
    assert review["consistency_check"]["blockers"] == []
    assert review["consistency_check"]["warnings"] == [
        {
            "code": "previous_summary_missing",
            "message": "Previous chapter summary is missing for chapter 2.",
            "field": "previous_summary",
        }
    ]
    assert review["committed"] is True
    assert review["committed_chapter_no"] == 2


def test_commit_suggestion_restores_formal_state_when_second_state_write_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "commit-project"
    create_project(
        project_root=str(project_root),
        title="Commit Novel",
        topic="xianxia",
        style="cold",
        target="serial",
    )
    snapshot_path = get_chapter_snapshot_path(str(project_root), 1)
    original_characters = {"characters": []}
    original_timeline = {"events": []}
    original_foreshadow = {"items": []}
    save_json(str(project_root / "characters.json"), original_characters)
    save_json(str(project_root / "timeline.json"), original_timeline)
    save_json(str(project_root / "foreshadow.json"), original_foreshadow)
    save_json(
        str(project_root / "suggestions" / "ch001.suggestion.json"),
        {
            "chapter_no": 1,
            "character_updates": [
                {"action": "add", "target": "Lin Yue", "content": "Enters the story."}
            ],
            "timeline_updates": [
                {"action": "add", "target": "chapter_1", "content": "The conflict begins."}
            ],
            "foreshadow_updates": [],
            "notes": "Suggestion only.",
        },
    )

    original_save_json = save_json

    def failing_save_json(path: str, data) -> None:
        if path == str(project_root / "timeline.json"):
            raise RuntimeError("timeline write failed")
        original_save_json(path, data)

    monkeypatch.setattr("core.workflow_service.save_json", failing_save_json)

    with pytest.raises(Exception, match="timeline state persistence: timeline write failed"):
        commit_suggestion(str(project_root), 1)

    review = load_json(get_chapter_review_path(str(project_root), 1))
    suggestion = load_json(str(project_root / "suggestions" / "ch001.suggestion.json"))
    snapshot = load_json(snapshot_path)
    assert load_json(str(project_root / "characters.json")) == original_characters
    assert load_json(str(project_root / "timeline.json")) == original_timeline
    assert load_json(str(project_root / "foreshadow.json")) == original_foreshadow
    assert review["committed"] is False
    assert review["committed_chapter_no"] is None
    assert "committed" not in suggestion
    assert "committed_chapter_no" not in suggestion
    assert snapshot["status"] == "restored"
    assert snapshot["state_before"] == {
        "characters": original_characters,
        "timeline": original_timeline,
        "foreshadow": original_foreshadow,
    }
    assert snapshot["last_error"] == "Failed during timeline state persistence: timeline write failed"


def test_commit_suggestion_restores_formal_state_and_markers_when_marker_write_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "commit-project"
    create_project(
        project_root=str(project_root),
        title="Commit Novel",
        topic="xianxia",
        style="cold",
        target="serial",
    )
    snapshot_path = get_chapter_snapshot_path(str(project_root), 1)
    original_characters = {"characters": []}
    original_timeline = {"events": []}
    original_foreshadow = {"items": []}
    save_json(str(project_root / "characters.json"), original_characters)
    save_json(str(project_root / "timeline.json"), original_timeline)
    save_json(str(project_root / "foreshadow.json"), original_foreshadow)
    suggestion_path = str(project_root / "suggestions" / "ch001.suggestion.json")
    save_json(
        suggestion_path,
        {
            "chapter_no": 1,
            "character_updates": [
                {"action": "add", "target": "Lin Yue", "content": "Enters the story."}
            ],
            "timeline_updates": [],
            "foreshadow_updates": [],
            "notes": "Suggestion only.",
        },
    )

    original_save_json = save_json
    failed_once = {"value": False}

    def failing_save_json(path: str, data) -> None:
        if (
            path == suggestion_path
            and isinstance(data, dict)
            and data.get("committed") is True
            and not failed_once["value"]
        ):
            failed_once["value"] = True
            raise RuntimeError("suggestion marker write failed")
        original_save_json(path, data)

    monkeypatch.setattr("core.workflow_service.save_json", failing_save_json)

    with pytest.raises(Exception, match="suggestion marker write failed"):
        commit_suggestion(str(project_root), 1)

    review = load_json(get_chapter_review_path(str(project_root), 1))
    suggestion = load_json(suggestion_path)
    snapshot = load_json(snapshot_path)
    assert load_json(str(project_root / "characters.json")) == original_characters
    assert load_json(str(project_root / "timeline.json")) == original_timeline
    assert load_json(str(project_root / "foreshadow.json")) == original_foreshadow
    assert review["committed"] is False
    assert review["committed_chapter_no"] is None
    assert "committed" not in suggestion
    assert "committed_chapter_no" not in suggestion
    assert snapshot["status"] == "restored"
    assert snapshot["state_before"] == {
        "characters": original_characters,
        "timeline": original_timeline,
        "foreshadow": original_foreshadow,
    }
    assert snapshot["last_error"] == "Failed during commit marker persistence: suggestion marker write failed"


def test_commit_suggestion_rerun_restores_unfinished_snapshot_then_continues_commit(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "commit-project"
    create_project(
        project_root=str(project_root),
        title="Commit Novel",
        topic="xianxia",
        style="cold",
        target="serial",
    )
    chapter_no = 1
    snapshot_path = get_chapter_snapshot_path(str(project_root), chapter_no)
    review_path = get_chapter_review_path(str(project_root), chapter_no)
    suggestion_path = str(project_root / "suggestions" / "ch001.suggestion.json")
    original_characters = {"characters": []}
    original_timeline = {"events": []}
    original_foreshadow = {"items": []}
    save_json(str(project_root / "characters.json"), {"characters": [{"name": "Dirty"}]})
    save_json(
        str(project_root / "timeline.json"),
        {"events": [{"chapter_no": 1, "action": "add", "target": "chapter_1", "event": "Dirty"}]},
    )
    save_json(str(project_root / "foreshadow.json"), {"items": []})
    save_json(
        suggestion_path,
        {
            "chapter_no": 1,
            "character_updates": [
                {"action": "add", "target": "Lin Yue", "content": "Enters the story."}
            ],
            "timeline_updates": [
                {"action": "add", "target": "chapter_1", "content": "The conflict begins."}
            ],
            "foreshadow_updates": [],
            "notes": "Suggestion only.",
            "committed": True,
            "committed_chapter_no": 1,
        },
    )
    save_json(
        review_path,
        {
            "version": 1,
            "chapter_no": 1,
            "created_at": "2026-03-28T12:00:00Z",
            "suggestion_path": suggestion_path,
            "approved_suggestion": {
                "chapter_no": 1,
                "character_updates": [
                    {"action": "add", "target": "Lin Yue", "content": "Enters the story."}
                ],
                "timeline_updates": [
                    {"action": "add", "target": "chapter_1", "content": "The conflict begins."}
                ],
                "foreshadow_updates": [],
                "notes": "Suggestion only.",
            },
            "consistency_check": {
                "version": 1,
                "checked_at": "2026-03-28T12:01:00Z",
                "blockers": [],
                "warnings": [],
            },
            "committed": False,
            "committed_chapter_no": None,
        },
    )
    save_json(
        snapshot_path,
        {
            "version": 1,
            "chapter_no": 1,
            "created_at": "2026-03-28T12:02:00Z",
            "status": "restored",
            "review_path": review_path,
            "suggestion_path": suggestion_path,
            "state_before": {
                "characters": original_characters,
                "timeline": original_timeline,
                "foreshadow": original_foreshadow,
            },
            "restored_at": "2026-03-28T12:03:00Z",
            "last_error": "previous failure",
        },
    )

    result = commit_suggestion(str(project_root), chapter_no)

    assert result == {
        "chapter_no": 1,
        "suggestion_path": suggestion_path,
        "characters_updated": 1,
        "timeline_updated": 1,
        "foreshadow_updated": 0,
    }
    assert not Path(snapshot_path).exists()
    assert load_json(str(project_root / "characters.json")) == {
        "characters": [
            {
                "name": "Lin Yue",
                "role": "unknown",
                "traits": [],
                "current_state": "Enters the story.",
            }
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
    assert load_json(str(project_root / "foreshadow.json")) == original_foreshadow


def test_commit_suggestion_cleans_stale_snapshot_and_returns_existing_commit_result(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "commit-project"
    create_project(
        project_root=str(project_root),
        title="Commit Novel",
        topic="xianxia",
        style="cold",
        target="serial",
    )
    chapter_no = 1
    snapshot_path = get_chapter_snapshot_path(str(project_root), chapter_no)
    review_path = get_chapter_review_path(str(project_root), chapter_no)
    suggestion_path = str(project_root / "suggestions" / "ch001.suggestion.json")
    committed_characters = {
        "characters": [
            {
                "name": "Lin Yue",
                "role": "unknown",
                "traits": [],
                "current_state": "Enters the story.",
            }
        ]
    }
    save_json(str(project_root / "characters.json"), committed_characters)
    save_json(
        str(project_root / "timeline.json"),
        {
            "events": [
                {
                    "chapter_no": 1,
                    "event": "The conflict begins.",
                    "action": "add",
                    "target": "chapter_1",
                }
            ]
        },
    )
    save_json(str(project_root / "foreshadow.json"), {"items": []})
    save_json(
        suggestion_path,
        {
            "chapter_no": 1,
            "character_updates": [
                {"action": "add", "target": "Lin Yue", "content": "Enters the story."}
            ],
            "timeline_updates": [
                {"action": "add", "target": "chapter_1", "content": "The conflict begins."}
            ],
            "foreshadow_updates": [],
            "notes": "Suggestion only.",
            "committed": True,
            "committed_chapter_no": 1,
        },
    )
    save_json(
        review_path,
        {
            "version": 1,
            "chapter_no": 1,
            "created_at": "2026-03-28T12:00:00Z",
            "suggestion_path": suggestion_path,
            "approved_suggestion": {
                "chapter_no": 1,
                "character_updates": [
                    {"action": "add", "target": "Lin Yue", "content": "Enters the story."}
                ],
                "timeline_updates": [
                    {"action": "add", "target": "chapter_1", "content": "The conflict begins."}
                ],
                "foreshadow_updates": [],
                "notes": "Suggestion only.",
            },
            "consistency_check": {
                "version": 1,
                "checked_at": "2026-03-28T12:01:00Z",
                "blockers": [],
                "warnings": [],
            },
            "committed": True,
            "committed_chapter_no": 1,
        },
    )
    save_json(
        snapshot_path,
        {
            "version": 1,
            "chapter_no": 1,
            "created_at": "2026-03-28T12:02:00Z",
            "status": "pending",
            "review_path": review_path,
            "suggestion_path": suggestion_path,
            "state_before": {
                "characters": {"characters": []},
                "timeline": {"events": []},
                "foreshadow": {"items": []},
            },
            "restored_at": None,
            "last_error": None,
        },
    )

    result = commit_suggestion(str(project_root), chapter_no)

    assert result == {
        "chapter_no": 1,
        "suggestion_path": suggestion_path,
        "characters_updated": 1,
        "timeline_updated": 1,
        "foreshadow_updated": 0,
    }
    assert not Path(snapshot_path).exists()
    assert load_json(str(project_root / "characters.json")) == committed_characters


def test_commit_suggestion_raises_when_stale_snapshot_cleanup_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "commit-project"
    create_project(
        project_root=str(project_root),
        title="Commit Novel",
        topic="xianxia",
        style="cold",
        target="serial",
    )
    chapter_no = 1
    snapshot_path = get_chapter_snapshot_path(str(project_root), chapter_no)
    review_path = get_chapter_review_path(str(project_root), chapter_no)
    suggestion_path = str(project_root / "suggestions" / "ch001.suggestion.json")
    committed_characters = {
        "characters": [
            {
                "name": "Lin Yue",
                "role": "unknown",
                "traits": [],
                "current_state": "Enters the story.",
            }
        ]
    }
    save_json(str(project_root / "characters.json"), committed_characters)
    save_json(str(project_root / "timeline.json"), {"events": []})
    save_json(str(project_root / "foreshadow.json"), {"items": []})
    save_json(
        suggestion_path,
        {
            "chapter_no": 1,
            "character_updates": [],
            "timeline_updates": [],
            "foreshadow_updates": [],
            "notes": "Suggestion only.",
            "committed": True,
            "committed_chapter_no": 1,
        },
    )
    save_json(
        review_path,
        {
            "version": 1,
            "chapter_no": 1,
            "created_at": "2026-03-28T12:00:00Z",
            "suggestion_path": suggestion_path,
            "approved_suggestion": {
                "chapter_no": 1,
                "character_updates": [],
                "timeline_updates": [],
                "foreshadow_updates": [],
                "notes": "Suggestion only.",
            },
            "consistency_check": {
                "version": 1,
                "checked_at": "2026-03-28T12:01:00Z",
                "blockers": [],
                "warnings": [],
            },
            "committed": True,
            "committed_chapter_no": 1,
        },
    )
    save_json(
        snapshot_path,
        {
            "version": 1,
            "chapter_no": 1,
            "created_at": "2026-03-28T12:02:00Z",
            "status": "pending",
            "review_path": review_path,
            "suggestion_path": suggestion_path,
            "state_before": {
                "characters": {"characters": []},
                "timeline": {"events": []},
                "foreshadow": {"items": []},
            },
            "restored_at": None,
            "last_error": None,
        },
    )
    monkeypatch.setattr(
        "core.longform.snapshot_service._delete_snapshot_file",
        lambda path: (_ for _ in ()).throw(PermissionError("snapshot delete blocked")),
    )

    with pytest.raises(Exception, match="stale snapshot cleanup"):
        commit_suggestion(str(project_root), chapter_no)

    assert Path(snapshot_path).exists()
    assert load_json(str(project_root / "characters.json")) == committed_characters
