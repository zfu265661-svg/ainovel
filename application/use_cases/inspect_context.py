from __future__ import annotations

from infrastructure.persistence.json_repository import JsonProjectRepository


def inspect_context(project_id: str, chapter_id: int) -> dict:
    return JsonProjectRepository().load_chapter_json(project_id, chapter_id, "context_audit.json")


def inspect_trace(project_id: str, chapter_id: int) -> dict:
    return JsonProjectRepository().load_chapter_json(project_id, chapter_id, "trace.json")


def inspect_report(project_id: str, chapter_id: int) -> dict:
    return JsonProjectRepository().load_chapter_json(project_id, chapter_id, "consistency_report.json")
