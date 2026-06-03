from __future__ import annotations

import json
from pathlib import Path

from core.longform.inspection_service import (
    build_context_inspection_report,
    build_plot_threads_inspection_report,
    build_story_bible_inspection_report,
)
from core.project_service import create_project_structure
from core.storage import save_json, save_text


def test_build_context_inspection_report_reuses_context_audit_and_sources(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "inspect-project"
    create_project_structure(
        str(project_root),
        title="Inspect Novel",
        topic="xianxia",
        style="cold",
        target="serial",
    )
    _save_outline_and_plan(project_root, chapter_no=2, goal="Lin Yue enters North Gate.")
    save_text(str(project_root / "docs" / "ch001.summary.md"), "Chapter one summary.")
    save_json(
        str(project_root / "characters.json"),
        {
            "characters": [
                {"name": "Lin Yue", "role": "protagonist"},
                {"name": "Distant Elder", "role": "mentor"},
            ]
        },
    )
    save_json(
        str(project_root / "timeline.json"),
        {"events": [{"chapter_no": 1, "event": "Lin Yue reached the wall."}]},
    )
    save_json(
        str(project_root / "foreshadow.json"),
        {"items": [{"id": "fs-1", "content": "Gate clue", "status": "open"}]},
    )
    save_json(
        str(project_root / "locations.json"),
        {"locations": [{"name": "North Gate", "description": "Cold checkpoint"}]},
    )
    save_json(
        str(project_root / "plot_threads.json"),
        {"threads": [{"id": "main", "summary": "North Gate pressure", "status": "active"}]},
    )

    report = build_context_inspection_report(str(project_root), 2)

    assert report["chapter_no"] == 2
    assert report["context_audit"]["chapter_no"] == 2
    assert report["context_audit"]["selection_basis"] == "chapter_plan_and_outline_text"
    assert report["selected_context_counts"]["characters"] == 1
    assert report["selected_context_counts"]["locations"] == 1
    assert report["selected_context_labels"]["characters"] == ["Lin Yue"]
    assert report["selected_context_labels"]["locations"] == ["North Gate"]
    assert report["summary_chain"]["previous_summary"]["exists"] is True
    assert report["summary_chain"]["previous_summary"]["selected"] is True
    assert report["sources"]["previous_summary_path"] == str(
        project_root / "docs" / "ch001.summary.md"
    )


def test_inspection_reports_support_legacy_project_without_phase3_state(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "legacy-inspect-project"
    project_root.mkdir()
    (project_root / "docs").mkdir()
    save_json(
        str(project_root / "project.json"),
        {
            "project_id": "legacy-inspect-project",
            "title": "Legacy Inspect Novel",
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
                    "goal": "Open the legacy story",
                    "status": "planned",
                }
            ]
        },
    )
    save_json(str(project_root / "characters.json"), {"characters": []})
    save_json(str(project_root / "timeline.json"), {"events": []})
    save_json(str(project_root / "foreshadow.json"), {"items": []})
    _save_outline_and_plan(project_root, chapter_no=1, goal="Open the legacy story.")

    context_report = build_context_inspection_report(str(project_root), 1)
    story_report = build_story_bible_inspection_report(str(project_root))
    plot_report = build_plot_threads_inspection_report(str(project_root))

    assert context_report["selected_context_counts"]["plot_threads"] == 0
    assert context_report["selected_context_counts"]["locations"] == 0
    assert context_report["selected_context_counts"]["organizations"] == 0
    assert story_report["enhanced_state_health"] == "missing_optional"
    assert story_report["missing_optional_files"] == [
        "story_bible.json",
        "plot_threads.json",
        "locations.json",
        "organizations.json",
        "style_guide.json",
        "scenes.json",
    ]
    assert plot_report["health"] == "missing_optional"
    assert plot_report["total"] == 0


def test_build_plot_threads_inspection_report_counts_statuses_and_graph_fields(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "plot-inspect-project"
    create_project_structure(
        str(project_root),
        title="Plot Inspect Novel",
        topic="xianxia",
        style="cold",
        target="serial",
    )
    save_json(
        str(project_root / "plot_threads.json"),
        {
            "threads": [
                {
                    "id": "main",
                    "type": "main",
                    "status": "active",
                    "nodes": [
                        {"id": "main-1", "unlocks": ["main-2"]},
                        {"id": "main-2", "depends_on": ["main-1"]},
                    ],
                },
                {
                    "id": "romance",
                    "type": "romance",
                    "status": "open",
                    "converges_to": "main",
                },
                {
                    "id": "old-secret",
                    "type": "conspiracy",
                    "status": "resolved",
                    "branch_id": "branch-a",
                    "merge_target_id": "main",
                },
                {"id": "quiet", "type": "subplot", "status": "dormant"},
            ]
        },
    )

    report = build_plot_threads_inspection_report(str(project_root))

    assert report["health"] == "healthy"
    assert report["total"] == 4
    assert report["status_counts"] == {
        "active": 1,
        "unresolved": 1,
        "resolved": 1,
        "dormant": 1,
        "unknown": 0,
    }
    assert report["type_counts"] == {
        "main": 1,
        "romance": 1,
        "conspiracy": 1,
        "subplot": 1,
    }
    assert report["graph"]["graph_fields_present"] is True
    assert report["graph"]["nodes"] == 2
    assert report["graph"]["depends_on_edges"] == 1
    assert report["graph"]["unlocks_edges"] == 1
    assert report["graph"]["converges_to_refs"] == 1
    assert report["graph"]["branch_refs"] == 1
    assert report["graph"]["merge_refs"] == 1


def _save_outline_and_plan(project_root: Path, chapter_no: int, goal: str) -> None:
    save_json(
        str(project_root / "chapters.json"),
        {
            "chapters": [
                {
                    "chapter_no": chapter_no,
                    "volume_no": 1,
                    "title": f"Chapter {chapter_no}",
                    "goal": goal,
                    "status": "planned",
                }
            ]
        },
    )
    save_text(
        str(project_root / "docs" / "outline.md"),
        "# Outline\n\n```json\n"
        + json.dumps({"title": "Inspect Outline", "theme": "continuity"}, indent=2)
        + "\n```\n",
    )
    save_text(
        str(project_root / "docs" / f"ch{chapter_no:03d}.plan.md"),
        "# Chapter Plan\n\n```json\n"
        + json.dumps(
            {
                "chapter_no": chapter_no,
                "volume_no": 1,
                "title": f"Chapter {chapter_no}",
                "goal": goal,
                "conflict": "Pressure",
                "beats": [],
                "ending_hook": "Continue",
                "status": "planned",
            },
            indent=2,
        )
        + "\n```\n",
    )
