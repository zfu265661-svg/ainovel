from __future__ import annotations

from pathlib import Path
from typing import Any

from core.longform.loop_state_service import (
    create_loop_state,
    load_loop_state,
    save_loop_state,
)


LOOP_STATE_FILE_NAME = "loop_state.json"
CHECKPOINTS_DIR_NAME = "checkpoints"
REVIEWS_DIR_NAME = "reviews"


def get_longform_file_paths(project_root: str) -> dict[str, str]:
    """Return the canonical file and directory paths for longform process state."""
    root = Path(project_root)
    return {
        "project_root": str(root),
        "loop_state_json": str(root / LOOP_STATE_FILE_NAME),
        "checkpoints_dir": str(root / CHECKPOINTS_DIR_NAME),
        "reviews_dir": str(root / REVIEWS_DIR_NAME),
    }


def ensure_longform_directories(project_root: str) -> dict[str, str]:
    """Create auxiliary longform directories without touching formal story state files."""
    paths = get_longform_file_paths(project_root)
    Path(paths["checkpoints_dir"]).mkdir(parents=True, exist_ok=True)
    Path(paths["reviews_dir"]).mkdir(parents=True, exist_ok=True)
    return paths


def initialize_loop_state(
    project_root: str,
    target_chapter_count: int,
    start_chapter_no: int = 1,
) -> dict[str, Any]:
    """Create the minimum loop_state.json for a future resumable longform workflow."""
    paths = ensure_longform_directories(project_root)
    loop_state_path = Path(paths["loop_state_json"])

    if loop_state_path.exists():
        raise FileExistsError(f"Loop state already exists: {loop_state_path}")

    state = create_loop_state(
        target_chapter_count=target_chapter_count,
        start_chapter_no=start_chapter_no,
    )
    save_loop_state(str(loop_state_path), state)
    return state


def loop_state_exists(project_root: str) -> bool:
    """Return whether the project already has loop_state.json."""
    paths = get_longform_file_paths(project_root)
    return Path(paths["loop_state_json"]).is_file()


def load_project_loop_state(project_root: str) -> dict[str, Any]:
    """Load loop_state.json for one project."""
    paths = get_longform_file_paths(project_root)
    return load_loop_state(paths["loop_state_json"])


def save_project_loop_state(project_root: str, state: dict[str, Any]) -> None:
    """Persist loop_state.json for one project."""
    paths = ensure_longform_directories(project_root)
    save_loop_state(paths["loop_state_json"], state)


def get_chapter_checkpoint_path(project_root: str, chapter_no: int) -> str:
    normalized_chapter_no = _normalize_chapter_no(chapter_no)
    paths = get_longform_file_paths(project_root)
    return str(Path(paths["checkpoints_dir"]) / f"ch{normalized_chapter_no:03d}.checkpoint.json")


def get_chapter_review_path(project_root: str, chapter_no: int) -> str:
    normalized_chapter_no = _normalize_chapter_no(chapter_no)
    paths = get_longform_file_paths(project_root)
    return str(Path(paths["reviews_dir"]) / f"ch{normalized_chapter_no:03d}.review.json")


def _normalize_chapter_no(chapter_no: int) -> int:
    if not isinstance(chapter_no, int) or chapter_no <= 0:
        raise ValueError("chapter_no must be a positive integer.")
    return chapter_no
