from __future__ import annotations

from domain.models.base import utc_now_iso
from domain.models.narrative_snapshot import NarrativeSnapshot
from domain.models.project import NovelProject
from infrastructure.persistence.json_repository import JsonProjectRepository


def create_project(name: str, project_id: str | None = None, description: str = "") -> dict:
    repo = JsonProjectRepository()
    safe_id = project_id or name.strip().lower().replace(" ", "-")
    project = NovelProject(project_id=safe_id, name=name, description=description, updated_at=utc_now_iso())
    snapshot = NarrativeSnapshot.empty(safe_id)
    snapshot.characters.append(
        {
            "id": "protagonist",
            "name": "Protagonist",
            "role": "lead",
            "traits": ["curious", "persistent"],
            "current_state": "Ready for chapter 1.",
        }
    )
    snapshot.locations.append(
        {
            "id": "starting-place",
            "name": "Starting Place",
            "description": "The initial location for the story.",
            "current_state": "Available.",
        }
    )
    snapshot.plot_threads.append(
        {
            "id": "main-thread",
            "title": "Main Thread",
            "status": "active",
            "introduced_chapter": 1,
            "last_seen_chapter": 0,
            "next_expected_chapter": 1,
            "related_characters": ["Protagonist"],
            "related_locations": ["Starting Place"],
            "notes": [],
            "risk": "ok",
        }
    )
    snapshot.foreshadows.append(
        {
            "id": "opening-hook",
            "title": "Opening Hook",
            "status": "active",
            "planted_chapter": 1,
            "expected_payoff_chapter": 3,
            "payoff_chapter": None,
            "risk": "ok",
            "notes": [],
        }
    )
    repo.save_project(project)
    repo.save_snapshot(snapshot)
    return {"project": project.to_dict(), "snapshot": snapshot.to_dict()}
