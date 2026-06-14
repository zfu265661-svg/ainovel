from __future__ import annotations

from pydantic import BaseModel
from fastapi import APIRouter

from application.use_cases.create_project import create_project
from application.use_cases.inspect_project import inspect_chapters, inspect_project, inspect_snapshot, list_projects


router = APIRouter()


class CreateProjectRequest(BaseModel):
    name: str
    project_id: str | None = None
    description: str = ""


@router.get("/projects")
def api_list_projects() -> list[dict]:
    return list_projects()


@router.post("/projects")
def api_create_project(payload: CreateProjectRequest) -> dict:
    return create_project(payload.name, project_id=payload.project_id, description=payload.description)


@router.get("/projects/{project_id}")
def api_get_project(project_id: str) -> dict:
    return inspect_project(project_id)


@router.get("/projects/{project_id}/snapshot")
def api_get_snapshot(project_id: str) -> dict:
    return inspect_snapshot(project_id)


@router.get("/projects/{project_id}/chapters")
def api_get_chapters(project_id: str) -> list[dict]:
    return inspect_chapters(project_id)
