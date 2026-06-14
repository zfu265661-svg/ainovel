from __future__ import annotations

from typing import Any


def render_chapter_plan(project_name: str, chapter_id: int, snapshot_hint: str = "") -> dict[str, Any]:
    return {
        "chapter_id": chapter_id,
        "title": f"Chapter {chapter_id}",
        "goal": f"Advance {project_name} chapter {chapter_id}.",
        "characters": [],
        "locations": [],
        "organizations": [],
        "plot_threads": [],
        "foreshadows": [],
        "handoff": snapshot_hint,
    }
