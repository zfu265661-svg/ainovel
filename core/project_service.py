from __future__ import annotations

from pathlib import Path
from typing import Any

from core.storage import load_json, save_json


PROJECT_FILE_NAME = "project.json"
CHAPTERS_FILE_NAME = "chapters.json"
CHARACTERS_FILE_NAME = "characters.json"
TIMELINE_FILE_NAME = "timeline.json"
FORESHADOW_FILE_NAME = "foreshadow.json"
DOCS_DIR_NAME = "docs"
SUGGESTIONS_DIR_NAME = "suggestions"


def create_project_structure(
    project_root: str,
    title: str,
    topic: str,
    style: str,
    target: str,
) -> dict[str, Any]:
    """Create the minimum Phase 1 project shell and return the saved metadata."""
    root = Path(project_root)
    paths = get_project_file_paths(project_root)

    if Path(paths["project_json"]).exists():
        raise FileExistsError(f"Project already exists: {root}")

    Path(paths["docs_dir"]).mkdir(parents=True, exist_ok=True)
    Path(paths["suggestions_dir"]).mkdir(parents=True, exist_ok=True)

    project = {
        "project_id": root.name,
        "title": title,
        "topic": topic,
        "style": style,
        "target": target,
        "current_chapter_no": 1,
        "status": "created",
    }
    save_json(paths["project_json"], project)
    save_json(paths["chapters_json"], {"chapters": []})
    save_json(paths["characters_json"], {"characters": []})
    save_json(paths["timeline_json"], {"events": []})
    save_json(paths["foreshadow_json"], {"items": []})

    return project


def load_project(project_root: str) -> dict[str, Any]:
    """Load project metadata from the project root."""
    data = load_json(get_project_file_paths(project_root)["project_json"])
    if not isinstance(data, dict):
        raise ValueError("Project metadata must be a JSON object.")
    return data


def get_project_file_paths(project_root: str) -> dict[str, str]:
    """Return the canonical file and directory paths for a project."""
    root = Path(project_root)
    return {
        "project_root": str(root),
        "project_json": str(root / PROJECT_FILE_NAME),
        "chapters_json": str(root / CHAPTERS_FILE_NAME),
        "characters_json": str(root / CHARACTERS_FILE_NAME),
        "timeline_json": str(root / TIMELINE_FILE_NAME),
        "foreshadow_json": str(root / FORESHADOW_FILE_NAME),
        "docs_dir": str(root / DOCS_DIR_NAME),
        "suggestions_dir": str(root / SUGGESTIONS_DIR_NAME),
    }


def get_chapter_plan_path(project_root: str, chapter_no: int) -> str:
    return _chapter_doc_path(project_root, chapter_no, "plan")


def get_chapter_draft_path(project_root: str, chapter_no: int) -> str:
    return _chapter_doc_path(project_root, chapter_no, "draft")


def get_chapter_rewrite_path(project_root: str, chapter_no: int) -> str:
    return _chapter_doc_path(project_root, chapter_no, "rewrite")


def get_chapter_summary_path(project_root: str, chapter_no: int) -> str:
    return _chapter_doc_path(project_root, chapter_no, "summary")


def get_chapter_suggestion_path(project_root: str, chapter_no: int) -> str:
    normalized_chapter_no = _normalize_chapter_no(chapter_no)
    root = Path(project_root)
    return str(root / SUGGESTIONS_DIR_NAME / f"ch{normalized_chapter_no:03d}.suggestion.json")


def _chapter_doc_path(project_root: str, chapter_no: int, suffix: str) -> str:
    normalized_chapter_no = _normalize_chapter_no(chapter_no)
    root = Path(project_root)
    return str(root / DOCS_DIR_NAME / f"ch{normalized_chapter_no:03d}.{suffix}.md")


def _normalize_chapter_no(chapter_no: int) -> int:
    if not isinstance(chapter_no, int) or chapter_no <= 0:
        raise ValueError("chapter_no must be a positive integer.")
    return chapter_no
