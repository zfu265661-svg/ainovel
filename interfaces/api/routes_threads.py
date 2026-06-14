from __future__ import annotations

from fastapi import APIRouter

from application.use_cases.inspect_plot_threads import inspect_foreshadows, inspect_plot_threads


router = APIRouter()


@router.get("/projects/{project_id}/plot-threads")
def api_get_plot_threads(project_id: str) -> list[dict]:
    return inspect_plot_threads(project_id)


@router.get("/projects/{project_id}/foreshadows")
def api_get_foreshadows(project_id: str) -> list[dict]:
    return inspect_foreshadows(project_id)
