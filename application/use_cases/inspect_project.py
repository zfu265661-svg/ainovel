from __future__ import annotations

from infrastructure.persistence.json_repository import JsonProjectRepository


def list_projects() -> list[dict]:
    return JsonProjectRepository().list_projects()


def inspect_project(project_id: str) -> dict:
    repo = JsonProjectRepository()
    project = repo.load_project(project_id)
    snapshot = repo.load_snapshot(project_id)
    return {
        "project": project.to_dict(),
        "snapshot": snapshot.to_dict(),
        "chapters": repo.list_chapters(project_id),
        "checkpoints": repo.list_checkpoints(project_id),
    }


def inspect_snapshot(project_id: str) -> dict:
    return JsonProjectRepository().load_snapshot(project_id).to_dict()


def inspect_chapters(project_id: str) -> list[dict]:
    return JsonProjectRepository().list_chapters(project_id)
