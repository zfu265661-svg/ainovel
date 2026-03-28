from __future__ import annotations

from importlib import import_module
from typing import Any


_EXPORTS = {
    "create_loop_state": ("core.longform.loop_state_service", "create_loop_state"),
    "ensure_longform_directories": (
        "core.longform.project_state_repository",
        "ensure_longform_directories",
    ),
    "get_chapter_checkpoint_path": (
        "core.longform.project_state_repository",
        "get_chapter_checkpoint_path",
    ),
    "get_chapter_review_path": (
        "core.longform.project_state_repository",
        "get_chapter_review_path",
    ),
    "get_longform_file_paths": (
        "core.longform.project_state_repository",
        "get_longform_file_paths",
    ),
    "get_resume_chapter_no": (
        "core.longform.loop_state_service",
        "get_resume_chapter_no",
    ),
    "initialize_loop_state": (
        "core.longform.project_state_repository",
        "initialize_loop_state",
    ),
    "load_loop_state": ("core.longform.loop_state_service", "load_loop_state"),
    "load_project_loop_state": (
        "core.longform.project_state_repository",
        "load_project_loop_state",
    ),
    "loop_state_exists": (
        "core.longform.project_state_repository",
        "loop_state_exists",
    ),
    "mark_chapter_completed": (
        "core.longform.loop_state_service",
        "mark_chapter_completed",
    ),
    "mark_chapter_failed": (
        "core.longform.loop_state_service",
        "mark_chapter_failed",
    ),
    "mark_chapter_started": (
        "core.longform.loop_state_service",
        "mark_chapter_started",
    ),
    "run_five_chapter_loop": (
        "core.longform.serial_workflow_service",
        "run_five_chapter_loop",
    ),
    "run_single_chapter": (
        "core.longform.chapter_runner_service",
        "run_single_chapter",
    ),
    "save_loop_state": ("core.longform.loop_state_service", "save_loop_state"),
    "save_project_loop_state": (
        "core.longform.project_state_repository",
        "save_project_loop_state",
    ),
}

__all__ = list(_EXPORTS)


def __getattr__(name: str) -> Any:
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_name, attribute_name = _EXPORTS[name]
    module = import_module(module_name)
    return getattr(module, attribute_name)


def __dir__() -> list[str]:
    return sorted(list(globals().keys()) + __all__)
