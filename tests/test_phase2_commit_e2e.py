from __future__ import annotations

from pathlib import Path

from core.longform.project_state_repository import get_chapter_review_path
from core.storage import load_json, load_text
from core.workflow_service import (
    commit_suggestion,
    create_project,
    plan_novel,
    write_chapter,
)


def test_phase1_full_creation_loop_with_commit_runs_end_to_end(
    monkeypatch,
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "phase1-commit-e2e"

    monkeypatch.setattr(
        "core.workflow_service.generate_outline",
        lambda topic, style, target: {
            "title": "Test Outline",
            "core_hook": "A hidden bloodline wakes.",
            "theme": "growth",
            "protagonist": {"name": "Lin Yue"},
            "conflict": {"main_conflict": "Clan and sect pressure."},
            "volume_plan": [],
        },
    )
    monkeypatch.setattr(
        "core.workflow_service.generate_volume_plan",
        lambda outline: [
            {
                "volume_no": 1,
                "title": "Volume One",
                "goal": "Open the main line",
                "core_conflict": "The protagonist is forced into conflict.",
                "planned_chapters": 1,
            }
        ],
    )
    monkeypatch.setattr(
        "core.workflow_service.generate_volume_chapters",
        lambda outline, volume_info, start_chapter_no: [
            {
                "chapter_no": start_chapter_no,
                "volume_no": volume_info["volume_no"],
                "title": "Chapter One",
                "goal": "Start the story",
                "conflict": "Initial pressure",
                "beats": [{"order": 1, "scene": "Opening scene"}],
                "ending_hook": "A stranger appears at the gate.",
                "status": "planned",
            }
        ],
    )
    monkeypatch.setattr(
        "core.workflow_service.generate_draft",
        lambda chapter_plan, context_bundle, style_rules: "draft body",
    )
    monkeypatch.setattr(
        "core.workflow_service.rewrite_text",
        lambda text: "rewritten body",
    )
    monkeypatch.setattr(
        "core.workflow_service.summarize_previous_chapter",
        lambda text, max_words=300: "chapter summary",
    )
    monkeypatch.setattr(
        "core.workflow_service.generate_state_suggestions",
        lambda chapter_no, outline, chapter_plan, rewritten_text, chapter_summary, characters, timeline, foreshadow: {
            "chapter_no": chapter_no,
            "character_updates": [
                {"action": "update", "target": "Lin Yue", "content": "Becomes more cautious."},
                {"action": "add", "target": "Su He", "content": "A mentor joins the cast."},
            ],
            "timeline_updates": [
                {"action": "add", "target": "chapter_1", "content": "The first conflict begins."}
            ],
            "foreshadow_updates": [
                {"action": "add", "target": "fs-1", "content": "A clue is planted."}
            ],
            "notes": "Suggestion only.",
        },
    )

    created = create_project(
        project_root=str(project_root),
        title="Phase 1 Commit E2E",
        topic="xianxia",
        style="cold",
        target="serial",
    )
    planned = plan_novel(str(project_root))
    written = write_chapter(str(project_root), 1)
    committed = commit_suggestion(str(project_root), 1)

    assert created["status"] == "created"
    assert planned["outline"]["title"] == "Test Outline"
    assert written["chapter_no"] == 1
    assert committed == {
        "chapter_no": 1,
        "suggestion_path": str(project_root / "suggestions" / "ch001.suggestion.json"),
        "characters_updated": 2,
        "timeline_updated": 1,
        "foreshadow_updated": 1,
    }

    assert load_json(str(project_root / "project.json"))["title"] == "Phase 1 Commit E2E"
    assert load_text(str(project_root / "docs" / "outline.md")).strip()
    assert load_text(str(project_root / "docs" / "volumes.md")).strip()
    assert load_text(str(project_root / "docs" / "ch001.plan.md")).strip()
    assert load_text(str(project_root / "docs" / "ch001.draft.md")) == "draft body"
    assert load_text(str(project_root / "docs" / "ch001.rewrite.md")) == "rewritten body"
    assert load_text(str(project_root / "docs" / "ch001.summary.md")) == "chapter summary"

    assert load_json(str(project_root / "characters.json")) == {
        "characters": [
            {
                "name": "Lin Yue",
                "role": "unknown",
                "traits": [],
                "current_state": "Becomes more cautious.",
            },
            {
                "name": "Su He",
                "role": "unknown",
                "traits": [],
                "current_state": "A mentor joins the cast.",
            },
        ]
    }
    assert load_json(str(project_root / "timeline.json")) == {
        "events": [
            {
                "chapter_no": 1,
                "event": "The first conflict begins.",
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
            }
        ]
    }

    suggestion = load_json(str(project_root / "suggestions" / "ch001.suggestion.json"))
    assert suggestion["committed"] is True
    assert suggestion["committed_chapter_no"] == 1
    review = load_json(get_chapter_review_path(str(project_root), 1))
    assert review["approved_suggestion"]["chapter_no"] == 1
    assert review["consistency_check"]["blockers"] == []
    assert review["consistency_check"]["warnings"] == []
    assert review["committed"] is True
    assert review["committed_chapter_no"] == 1
