from __future__ import annotations

from pathlib import Path

from core.storage import load_json, load_text
from core.workflow_service import create_project, plan_novel


def test_plan_novel_generates_outline_volumes_chapters_and_plan_docs(
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

    monkeypatch.setattr(
        "core.workflow_service.generate_outline",
        lambda topic, style, target: {
            "title": "Test Outline",
            "core_hook": "A hook",
            "theme": "growth",
            "protagonist": {"name": "Lin Yue"},
            "conflict": {"main_conflict": "A central conflict"},
            "volume_plan": [],
        },
    )
    monkeypatch.setattr(
        "core.workflow_service.generate_volume_plan",
        lambda outline: [
            {
                "volume_no": 1,
                "title": "Volume One",
                "goal": "Set up the main line",
                "core_conflict": "Clan pressure",
                "planned_chapters": 2,
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
                "goal": "Open the story",
                "conflict": "Initial trouble",
                "beats": [{"order": 1, "scene": "Opening"}],
                "ending_hook": "A knock at the gate",
                "status": "planned",
            },
            {
                "chapter_no": start_chapter_no + 1,
                "volume_no": volume_info["volume_no"],
                "title": "Chapter Two",
                "goal": "Raise the tension",
                "conflict": "Enemy pressure",
                "beats": [{"order": 1, "scene": "Confrontation"}],
                "ending_hook": "A new clue appears",
                "status": "planned",
            },
        ],
    )

    result = plan_novel(str(project_root))

    assert result["outline"]["title"] == "Test Outline"
    assert result["volume_plan"][0]["title"] == "Volume One"
    assert result["chapters"] == [
        {
            "chapter_no": 1,
            "volume_no": 1,
            "title": "Chapter One",
            "goal": "Open the story",
            "status": "planned",
        },
        {
            "chapter_no": 2,
            "volume_no": 1,
            "title": "Chapter Two",
            "goal": "Raise the tension",
            "status": "planned",
        },
    ]

    outline_text = load_text(str(project_root / "docs" / "outline.md"))
    volumes_text = load_text(str(project_root / "docs" / "volumes.md"))
    chapters_index = load_json(str(project_root / "chapters.json"))
    plan_one = load_text(str(project_root / "docs" / "ch001.plan.md"))
    plan_two = load_text(str(project_root / "docs" / "ch002.plan.md"))

    assert "Test Outline" in outline_text
    assert "Volume One" in volumes_text
    assert chapters_index == {
        "chapters": [
            {
                "chapter_no": 1,
                "volume_no": 1,
                "title": "Chapter One",
                "goal": "Open the story",
                "status": "planned",
            },
            {
                "chapter_no": 2,
                "volume_no": 1,
                "title": "Chapter Two",
                "goal": "Raise the tension",
                "status": "planned",
            },
        ]
    }
    assert "Chapter One" in plan_one
    assert "Chapter Two" in plan_two
    assert len(chapters_index["chapters"]) == 2
