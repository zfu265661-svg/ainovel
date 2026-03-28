from __future__ import annotations

from pathlib import Path

import pytest

from core.longform.project_state_repository import (
    ensure_longform_directories,
    get_chapter_checkpoint_path,
    get_chapter_review_path,
    get_chapter_snapshot_path,
    get_longform_file_paths,
    initialize_loop_state,
    load_project_loop_state,
    loop_state_exists,
    save_project_loop_state,
)
from core.project_service import create_project_structure
from core.storage import load_json


def test_initialize_loop_state_creates_only_longform_process_files(tmp_path: Path) -> None:
    project_root = tmp_path / "longform-project"
    create_project_structure(
        str(project_root),
        title="Test Novel",
        topic="xianxia",
        style="cold",
        target="serial",
    )
    original_characters = load_json(str(project_root / "characters.json"))
    original_timeline = load_json(str(project_root / "timeline.json"))
    original_foreshadow = load_json(str(project_root / "foreshadow.json"))

    state = initialize_loop_state(str(project_root), target_chapter_count=5)

    assert state["next_chapter_no"] == 1
    assert loop_state_exists(str(project_root)) is True
    assert load_project_loop_state(str(project_root)) == state
    assert (project_root / "checkpoints").is_dir()
    assert (project_root / "reviews").is_dir()
    assert not (project_root / "snapshots").exists()
    assert load_json(str(project_root / "characters.json")) == original_characters
    assert load_json(str(project_root / "timeline.json")) == original_timeline
    assert load_json(str(project_root / "foreshadow.json")) == original_foreshadow


def test_save_project_loop_state_round_trips_through_repository(tmp_path: Path) -> None:
    project_root = tmp_path / "longform-project"
    ensure_longform_directories(str(project_root))
    initial_state = initialize_loop_state(str(project_root), target_chapter_count=5)

    updated_state = {**initial_state, "status": "failed", "current_chapter_no": 1}
    save_project_loop_state(str(project_root), updated_state)

    assert load_project_loop_state(str(project_root)) == updated_state


def test_initialize_loop_state_rejects_duplicate_creation(tmp_path: Path) -> None:
    project_root = tmp_path / "longform-project"
    ensure_longform_directories(str(project_root))
    initialize_loop_state(str(project_root), target_chapter_count=5)

    with pytest.raises(FileExistsError, match="Loop state already exists"):
        initialize_loop_state(str(project_root), target_chapter_count=5)


def test_longform_paths_use_canonical_naming_rules(tmp_path: Path) -> None:
    project_root = tmp_path / "longform-project"

    paths = get_longform_file_paths(str(project_root))

    assert paths["loop_state_json"] == str(project_root / "loop_state.json")
    assert get_chapter_checkpoint_path(str(project_root), 2) == str(
        project_root / "checkpoints" / "ch002.checkpoint.json"
    )
    assert get_chapter_review_path(str(project_root), 7) == str(
        project_root / "reviews" / "ch007.review.json"
    )
    assert get_chapter_snapshot_path(str(project_root), 9) == str(
        project_root / "snapshots" / "ch009.snapshot.json"
    )
