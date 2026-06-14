from __future__ import annotations

from infrastructure.persistence.json_repository import JsonProjectRepository


def inspect_checkpoints(project_id: str) -> list[dict]:
    return JsonProjectRepository().list_checkpoints(project_id)
