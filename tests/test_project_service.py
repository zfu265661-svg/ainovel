from __future__ import annotations

from pathlib import Path

import pytest

from core.project_service import (
    create_project_structure,
    get_chapter_draft_path,
    get_chapter_plan_path,
    get_chapter_rewrite_path,
    get_chapter_summary_path,
    get_chapter_suggestion_path,
    get_project_file_paths,
    load_project,
)
from core.storage import load_json


def test_create_project_structure_creates_minimum_phase1_files(tmp_path: Path) -> None:
    project_root = tmp_path / "my-novel"

    result = create_project_structure(
        str(project_root),
        title="Test Novel",
        topic="xianxia",
        style="cold",
        target="serial",
    )

    assert result == {
        "project_id": "my-novel",
        "title": "Test Novel",
        "topic": "xianxia",
        "style": "cold",
        "target": "serial",
        "current_chapter_no": 1,
        "status": "created",
    }

    paths = get_project_file_paths(str(project_root))
    assert Path(paths["docs_dir"]).is_dir()
    assert Path(paths["suggestions_dir"]).is_dir()
    assert load_json(paths["project_json"]) == result
    assert load_json(paths["chapters_json"]) == {"chapters": []}
    assert load_json(paths["characters_json"]) == {"characters": []}
    assert load_json(paths["timeline_json"]) == {"events": []}
    assert load_json(paths["foreshadow_json"]) == {"items": []}


def test_load_project_returns_project_metadata(tmp_path: Path) -> None:
    project_root = tmp_path / "novel-project"
    expected = create_project_structure(
        str(project_root),
        title="Lin Yue",
        topic="urban fantasy",
        style="sharp",
        target="web serial",
    )

    assert load_project(str(project_root)) == expected


def test_get_chapter_paths_use_canonical_naming_rule(tmp_path: Path) -> None:
    project_root = tmp_path / "novel-project"

    assert get_chapter_plan_path(str(project_root), 1) == str(
        project_root / "docs" / "ch001.plan.md"
    )
    assert get_chapter_draft_path(str(project_root), 12) == str(
        project_root / "docs" / "ch012.draft.md"
    )
    assert get_chapter_rewrite_path(str(project_root), 123) == str(
        project_root / "docs" / "ch123.rewrite.md"
    )
    assert get_chapter_summary_path(str(project_root), 2) == str(
        project_root / "docs" / "ch002.summary.md"
    )
    assert get_chapter_suggestion_path(str(project_root), 9) == str(
        project_root / "suggestions" / "ch009.suggestion.json"
    )


def test_create_project_structure_raises_when_project_already_exists(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "repeat-project"
    create_project_structure(
        str(project_root),
        title="First Novel",
        topic="xianxia",
        style="cold",
        target="serial",
    )

    with pytest.raises(FileExistsError, match="Project already exists"):
        create_project_structure(
            str(project_root),
            title="Second Novel",
            topic="sci-fi",
            style="fast",
            target="print",
        )


@pytest.mark.parametrize("chapter_no", [0, -1, "1"])
def test_chapter_path_helpers_reject_invalid_chapter_numbers(
    tmp_path: Path,
    chapter_no: object,
) -> None:
    project_root = tmp_path / "novel-project"

    with pytest.raises(ValueError, match="chapter_no must be a positive integer"):
        get_chapter_plan_path(str(project_root), chapter_no)  # type: ignore[arg-type]
