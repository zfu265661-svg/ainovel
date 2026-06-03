from __future__ import annotations

import json
from pathlib import Path

from core.storage import load_json, load_text, save_json, save_text
from core.workflow_service import create_project, write_chapter


def test_write_chapter_generates_all_outputs_without_mutating_state_files(
    monkeypatch,
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "phase1-project"
    create_project(
        project_root=str(project_root),
        title="Phase 1 Novel",
        topic="xianxia",
        style="cold",
        target="serial",
    )

    save_json(
        str(project_root / "chapters.json"),
        {
            "chapters": [
                {
                    "chapter_no": 1,
                    "volume_no": 1,
                    "title": "Chapter One",
                    "goal": "Open the story",
                    "status": "planned",
                }
            ]
        },
    )
    save_json(
        str(project_root / "characters.json"),
        {
            "characters": [
                {
                    "name": "Lin Yue",
                    "role": "protagonist",
                    "traits": ["calm", "careful"],
                    "current_state": "Still hiding his true strength.",
                    "unused_field": "should not be passed through",
                }
            ]
        },
    )
    save_json(
        str(project_root / "timeline.json"),
        {
            "events": [
                {"chapter_no": 0, "event": "Prologue event"},
                {"chapter_no": 1, "event": "Current chapter should not leak in"},
                {"chapter_no": 2, "event": "Future event 1"},
                {"chapter_no": 3, "event": "Future event 2"},
                {"chapter_no": 4, "event": "Future event 3"},
                {"chapter_no": 5, "event": "Future event 4"},
                {"chapter_no": 6, "event": "Future event 5"},
            ]
        },
    )
    save_json(
        str(project_root / "foreshadow.json"),
        {
            "items": [
                {"id": "fs-1", "content": "Old clue", "status": "open"},
                {"id": "fs-2", "content": "Resolved clue", "status": "resolved"},
            ]
        },
    )
    save_json(
        str(project_root / "story_bible.json"),
        {
            "version": 1,
            "world": {"name": "Mirror City"},
            "rules": ["Mirrors remember vows."],
        },
    )
    save_json(
        str(project_root / "plot_threads.json"),
        {"threads": [{"id": "main", "summary": "Open the story", "status": "active"}]},
    )
    save_json(
        str(project_root / "locations.json"),
        {"locations": [{"name": "Opening", "description": "The opening place"}]},
    )
    save_json(
        str(project_root / "organizations.json"),
        {"organizations": [{"name": "Initial trouble", "goals": ["Pressure"]}]},
    )
    save_json(
        str(project_root / "style_guide.json"),
        {"version": 1, "voice": "cold"},
    )
    save_json(
        str(project_root / "scenes.json"),
        {"scenes": [{"id": "ch001-sc001", "chapter_no": 1, "goal": "Opening"}]},
    )
    save_text(
        str(project_root / "docs" / "outline.md"),
        "# 总纲\n\n```json\n"
        + json.dumps({"title": "Test Outline", "theme": "growth"}, ensure_ascii=False, indent=2)
        + "\n```\n",
    )
    save_text(
        str(project_root / "docs" / "ch001.plan.md"),
        "# 章节规划\n\n```json\n"
        + json.dumps(
            {
                "chapter_no": 1,
                "volume_no": 1,
                "title": "Chapter One",
                "goal": "Open the story",
                "conflict": "Initial trouble",
                "beats": [{"order": 1, "scene": "Opening"}],
                "ending_hook": "A knock at the gate",
                "status": "planned",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n```\n",
    )

    original_characters = load_json(str(project_root / "characters.json"))
    original_timeline = load_json(str(project_root / "timeline.json"))
    original_foreshadow = load_json(str(project_root / "foreshadow.json"))

    def fake_generate_draft(chapter_plan, context_bundle, style_rules):
        assert chapter_plan["title"] == "Chapter One"
        assert context_bundle["outline"]["title"] == "Test Outline"
        assert context_bundle["previous_summary"] == ""
        assert context_bundle["characters"] == [
            {
                "name": "Lin Yue",
                "role": "protagonist",
                "traits": ["calm", "careful"],
                "current_state": "Still hiding his true strength.",
            }
        ]
        assert context_bundle["timeline"] == [{"chapter_no": 0, "event": "Prologue event"}]
        assert context_bundle["foreshadow"] == [
            {"id": "fs-1", "content": "Old clue", "status": "open"}
        ]
        assert context_bundle["story_bible"] == {
            "version": 1,
            "world": {"name": "Mirror City"},
            "rules": ["Mirrors remember vows."],
        }
        assert context_bundle["plot_threads"] == [
            {"id": "main", "summary": "Open the story", "status": "active"}
        ]
        assert context_bundle["locations"] == [
            {"name": "Opening", "description": "The opening place"}
        ]
        assert context_bundle["organizations"] == [
            {"name": "Initial trouble", "goals": ["Pressure"]}
        ]
        assert context_bundle["style_guide"] == {"version": 1, "voice": "cold"}
        assert context_bundle["scenes"] == [
            {"id": "ch001-sc001", "chapter_no": 1, "goal": "Opening"}
        ]
        assert context_bundle["context_audit"]["chapter_no"] == 1
        assert style_rules == "cold"
        return "draft body"

    def fake_rewrite_text(text: str) -> str:
        assert text == "draft body"
        return "rewritten body"

    def fake_summarize_previous_chapter(text: str, max_words: int = 300) -> str:
        assert text == "rewritten body"
        return "chapter summary"

    def fake_generate_state_suggestions(
        chapter_no,
        outline,
        chapter_plan,
        rewritten_text,
        chapter_summary,
        characters,
        timeline,
        foreshadow,
    ):
        assert chapter_no == 1
        assert outline["title"] == "Test Outline"
        assert chapter_plan["title"] == "Chapter One"
        assert rewritten_text == "rewritten body"
        assert chapter_summary == "chapter summary"
        assert characters == [
            {
                "name": "Lin Yue",
                "role": "protagonist",
                "traits": ["calm", "careful"],
                "current_state": "Still hiding his true strength.",
                "unused_field": "should not be passed through",
            }
        ]
        assert timeline == [
            {"chapter_no": 0, "event": "Prologue event"},
            {"chapter_no": 1, "event": "Current chapter should not leak in"},
            {"chapter_no": 2, "event": "Future event 1"},
            {"chapter_no": 3, "event": "Future event 2"},
            {"chapter_no": 4, "event": "Future event 3"},
            {"chapter_no": 5, "event": "Future event 4"},
            {"chapter_no": 6, "event": "Future event 5"},
        ]
        assert foreshadow == [
            {"id": "fs-1", "content": "Old clue", "status": "open"},
            {"id": "fs-2", "content": "Resolved clue", "status": "resolved"},
        ]
        return {
            "chapter_no": 1,
            "character_updates": [
                {"action": "update", "target": "Lin Yue", "content": "More cautious."}
            ],
            "timeline_updates": [
                {"action": "add", "target": "chapter_1", "content": "Story opens."}
            ],
            "foreshadow_updates": [
                {"action": "add", "target": "fs-1", "content": "Clue gains meaning."}
            ],
            "notes": "Suggestion only.",
        }

    monkeypatch.setattr("core.workflow_service.generate_draft", fake_generate_draft)
    monkeypatch.setattr("core.workflow_service.rewrite_text", fake_rewrite_text)
    monkeypatch.setattr(
        "core.workflow_service.summarize_previous_chapter",
        fake_summarize_previous_chapter,
    )
    monkeypatch.setattr(
        "core.workflow_service.generate_state_suggestions",
        fake_generate_state_suggestions,
    )

    result = write_chapter(str(project_root), 1)

    assert result == {
        "chapter_no": 1,
        "draft_path": str(project_root / "docs" / "ch001.draft.md"),
        "rewrite_path": str(project_root / "docs" / "ch001.rewrite.md"),
        "summary_path": str(project_root / "docs" / "ch001.summary.md"),
        "suggestion_path": str(project_root / "suggestions" / "ch001.suggestion.json"),
    }
    assert load_text(result["draft_path"]) == "draft body"
    assert load_text(result["rewrite_path"]) == "rewritten body"
    assert load_text(result["summary_path"]) == "chapter summary"
    assert load_json(result["suggestion_path"]) == {
        "chapter_no": 1,
        "character_updates": [
            {"action": "update", "target": "Lin Yue", "content": "More cautious."}
        ],
        "timeline_updates": [
            {"action": "add", "target": "chapter_1", "content": "Story opens."}
        ],
        "foreshadow_updates": [
            {"action": "add", "target": "fs-1", "content": "Clue gains meaning."}
        ],
        "notes": "Suggestion only.",
    }
    assert load_json(str(project_root / "characters.json")) == original_characters
    assert load_json(str(project_root / "timeline.json")) == original_timeline
    assert load_json(str(project_root / "foreshadow.json")) == original_foreshadow


def test_write_chapter_passes_only_recent_timeline_history_to_draft(
    monkeypatch,
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "phase1-project"
    create_project(
        project_root=str(project_root),
        title="Phase 1 Novel",
        topic="xianxia",
        style="cold",
        target="serial",
    )

    save_json(
        str(project_root / "chapters.json"),
        {
            "chapters": [
                {
                    "chapter_no": 7,
                    "volume_no": 1,
                    "title": "Chapter Seven",
                    "goal": "Continue the story",
                    "status": "planned",
                }
            ]
        },
    )
    save_json(str(project_root / "characters.json"), {"characters": []})
    save_json(
        str(project_root / "timeline.json"),
        {
            "events": [
                {"chapter_no": 1, "event": "Event 1"},
                {"chapter_no": 2, "event": "Event 2"},
                {"chapter_no": 3, "event": "Event 3"},
                {"chapter_no": 4, "event": "Event 4"},
                {"chapter_no": 5, "event": "Event 5"},
                {"chapter_no": 6, "event": "Event 6"},
                {"chapter_no": 7, "event": "Current chapter event"},
            ]
        },
    )
    save_json(str(project_root / "foreshadow.json"), {"items": []})
    save_text(
        str(project_root / "docs" / "outline.md"),
        "# 鎬荤翰\n\n```json\n"
        + json.dumps({"title": "Test Outline", "theme": "growth"}, ensure_ascii=False, indent=2)
        + "\n```\n",
    )
    save_text(
        str(project_root / "docs" / "ch007.plan.md"),
        "# 绔犺妭瑙勫垝\n\n```json\n"
        + json.dumps(
            {
                "chapter_no": 7,
                "volume_no": 1,
                "title": "Chapter Seven",
                "goal": "Continue the story",
                "conflict": "Escalation",
                "beats": [{"order": 1, "scene": "Opening"}],
                "ending_hook": "A knock at the gate",
                "status": "planned",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n```\n",
    )

    def fake_generate_draft(chapter_plan, context_bundle, style_rules):
        assert context_bundle["timeline"] == [
            {"chapter_no": 2, "event": "Event 2"},
            {"chapter_no": 3, "event": "Event 3"},
            {"chapter_no": 4, "event": "Event 4"},
            {"chapter_no": 5, "event": "Event 5"},
            {"chapter_no": 6, "event": "Event 6"},
        ]
        return "draft body"

    monkeypatch.setattr("core.workflow_service.generate_draft", fake_generate_draft)
    monkeypatch.setattr("core.workflow_service.rewrite_text", lambda text: "rewritten body")
    monkeypatch.setattr(
        "core.workflow_service.summarize_previous_chapter",
        lambda text, max_words=300: "chapter summary",
    )
    monkeypatch.setattr(
        "core.workflow_service.generate_state_suggestions",
        lambda chapter_no, outline, chapter_plan, rewritten_text, chapter_summary, characters, timeline, foreshadow: {
            "chapter_no": chapter_no,
            "character_updates": [],
            "timeline_updates": [],
            "foreshadow_updates": [],
            "notes": "Suggestion only.",
        },
    )

    result = write_chapter(str(project_root), 7)

    assert result["chapter_no"] == 7


def test_write_chapter_supports_legacy_project_without_phase3_state_files(
    monkeypatch,
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "legacy-phase1-project"
    project_root.mkdir()
    save_json(
        str(project_root / "project.json"),
        {
            "project_id": "legacy-phase1-project",
            "title": "Legacy Phase 1 Novel",
            "topic": "xianxia",
            "style": "cold",
            "target": "serial",
            "current_chapter_no": 1,
            "status": "created",
        },
    )
    save_json(
        str(project_root / "chapters.json"),
        {
            "chapters": [
                {
                    "chapter_no": 1,
                    "volume_no": 1,
                    "title": "Legacy Chapter",
                    "goal": "Open the legacy project",
                    "status": "planned",
                }
            ]
        },
    )
    save_json(str(project_root / "characters.json"), {"characters": []})
    save_json(str(project_root / "timeline.json"), {"events": []})
    save_json(str(project_root / "foreshadow.json"), {"items": []})
    save_text(
        str(project_root / "docs" / "outline.md"),
        "# 总纲\n\n```json\n"
        + json.dumps({"title": "Legacy Outline", "theme": "survival"}, ensure_ascii=False, indent=2)
        + "\n```\n",
    )
    save_text(
        str(project_root / "docs" / "ch001.plan.md"),
        "# 章节规划\n\n```json\n"
        + json.dumps(
            {
                "chapter_no": 1,
                "volume_no": 1,
                "title": "Legacy Chapter",
                "goal": "Open the legacy project",
                "conflict": "Old shell",
                "beats": [{"order": 1, "scene": "Opening"}],
                "ending_hook": "Continue",
                "status": "planned",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n```\n",
    )

    for optional_name in (
        "story_bible.json",
        "plot_threads.json",
        "locations.json",
        "organizations.json",
        "style_guide.json",
        "scenes.json",
    ):
        assert not (project_root / optional_name).exists()

    def fake_generate_draft(chapter_plan, context_bundle, style_rules):
        assert chapter_plan["title"] == "Legacy Chapter"
        assert context_bundle["story_bible"]["version"] == 1
        assert context_bundle["plot_threads"] == []
        assert context_bundle["locations"] == []
        assert context_bundle["organizations"] == []
        assert context_bundle["style_guide"]["version"] == 1
        assert context_bundle["scenes"] == []
        return "legacy draft"

    monkeypatch.setattr("core.workflow_service.generate_draft", fake_generate_draft)
    monkeypatch.setattr("core.workflow_service.rewrite_text", lambda text: "legacy rewrite")
    monkeypatch.setattr(
        "core.workflow_service.summarize_previous_chapter",
        lambda text, max_words=300: "legacy summary",
    )
    monkeypatch.setattr(
        "core.workflow_service.generate_state_suggestions",
        lambda chapter_no, outline, chapter_plan, rewritten_text, chapter_summary, characters, timeline, foreshadow: {
            "chapter_no": chapter_no,
            "character_updates": [],
            "timeline_updates": [],
            "foreshadow_updates": [],
            "notes": "Legacy suggestion only.",
        },
    )

    result = write_chapter(str(project_root), 1)

    assert result["chapter_no"] == 1
    assert load_text(result["draft_path"]) == "legacy draft"
    assert load_text(result["rewrite_path"]) == "legacy rewrite"
    assert load_text(result["summary_path"]) == "legacy summary"
    assert load_json(result["suggestion_path"])["notes"] == "Legacy suggestion only."
    for optional_name in (
        "story_bible.json",
        "plot_threads.json",
        "locations.json",
        "organizations.json",
        "style_guide.json",
        "scenes.json",
    ):
        assert not (project_root / optional_name).exists()
