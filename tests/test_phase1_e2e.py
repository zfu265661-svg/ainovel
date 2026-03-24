from __future__ import annotations

from pathlib import Path

from core.storage import load_json, load_text
from core.workflow_service import create_project, plan_novel, write_chapter


def test_phase1_minimum_loop_runs_end_to_end_with_mocked_generation(
    monkeypatch,
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "phase1-e2e"

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
                {"action": "update", "target": "Lin Yue", "content": "Becomes more cautious."}
            ],
            "timeline_updates": [
                {"action": "add", "target": "chapter_1", "content": "The conflict begins."}
            ],
            "foreshadow_updates": [
                {"action": "add", "target": "fs-1", "content": "A clue is planted."}
            ],
            "notes": "Suggestion only.",
        },
    )

    created = create_project(
        project_root=str(project_root),
        title="Phase 1 E2E",
        topic="xianxia",
        style="cold",
        target="serial",
    )
    planned = plan_novel(str(project_root))
    written = write_chapter(str(project_root), 1)

    assert created["status"] == "created"
    assert planned["outline"]["title"] == "Test Outline"
    assert planned["chapters"] == [
        {
            "chapter_no": 1,
            "volume_no": 1,
            "title": "Chapter One",
            "goal": "Start the story",
            "status": "planned",
        }
    ]
    assert written["chapter_no"] == 1

    assert load_json(str(project_root / "project.json"))["title"] == "Phase 1 E2E"
    assert load_text(str(project_root / "docs" / "outline.md")).strip()
    assert load_text(str(project_root / "docs" / "volumes.md")).strip()
    assert load_json(str(project_root / "chapters.json")) == {
        "chapters": [
            {
                "chapter_no": 1,
                "volume_no": 1,
                "title": "Chapter One",
                "goal": "Start the story",
                "status": "planned",
            }
        ]
    }
    assert load_text(str(project_root / "docs" / "ch001.plan.md")).strip()
    assert load_text(str(project_root / "docs" / "ch001.draft.md")) == "draft body"
    assert load_text(str(project_root / "docs" / "ch001.rewrite.md")) == "rewritten body"
    assert load_text(str(project_root / "docs" / "ch001.summary.md")) == "chapter summary"
    assert load_json(str(project_root / "suggestions" / "ch001.suggestion.json")) == {
        "chapter_no": 1,
        "character_updates": [
            {"action": "update", "target": "Lin Yue", "content": "Becomes more cautious."}
        ],
        "timeline_updates": [
            {"action": "add", "target": "chapter_1", "content": "The conflict begins."}
        ],
        "foreshadow_updates": [
            {"action": "add", "target": "fs-1", "content": "A clue is planted."}
        ],
        "notes": "Suggestion only.",
    }
