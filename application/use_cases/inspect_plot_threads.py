from __future__ import annotations

from infrastructure.persistence.json_repository import JsonProjectRepository


def inspect_plot_threads(project_id: str) -> list[dict]:
    snapshot = JsonProjectRepository().load_snapshot(project_id)
    return snapshot.plot_threads


def inspect_foreshadows(project_id: str) -> list[dict]:
    snapshot = JsonProjectRepository().load_snapshot(project_id)
    return snapshot.foreshadows
