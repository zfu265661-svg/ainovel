from __future__ import annotations

from pathlib import Path

import pytest

from core.foreshadow_service import (
    ForeshadowNotFoundError,
    ForeshadowValidationError,
    add_foreshadow,
    load_foreshadows,
    mark_foreshadow_resolved,
)


def test_add_and_load_foreshadow(tmp_path: Path) -> None:
    file_path = tmp_path / "foreshadowing.json"

    add_foreshadow(
        {
            "id": "fs-001",
            "content": "The broken jade pendant reacts to moonlight.",
            "introduced_in": "chapter_3",
            "payoff_planned": "chapter_12",
        },
        str(file_path),
    )

    assert load_foreshadows(str(file_path)) == [
        {
            "id": "fs-001",
            "content": "The broken jade pendant reacts to moonlight.",
            "introduced_in": "chapter_3",
            "payoff_planned": "chapter_12",
            "status": "open",
        }
    ]


def test_mark_foreshadow_resolved_updates_status(tmp_path: Path) -> None:
    file_path = tmp_path / "foreshadowing.json"

    add_foreshadow(
        {
            "id": "fs-001",
            "content": "The broken jade pendant reacts to moonlight.",
            "introduced_in": "chapter_3",
            "payoff_planned": "chapter_12",
            "status": "open",
        },
        str(file_path),
    )

    mark_foreshadow_resolved("fs-001", str(file_path))

    assert load_foreshadows(str(file_path))[0]["status"] == "resolved"


def test_add_foreshadow_raises_for_missing_required_fields(tmp_path: Path) -> None:
    file_path = tmp_path / "foreshadowing.json"

    with pytest.raises(
        ForeshadowValidationError,
        match="missing required field\\(s\\): payoff_planned",
    ):
        add_foreshadow(
            {
                "id": "fs-001",
                "content": "The broken jade pendant reacts to moonlight.",
                "introduced_in": "chapter_3",
            },
            str(file_path),
        )


def test_mark_foreshadow_resolved_raises_for_missing_id(tmp_path: Path) -> None:
    file_path = tmp_path / "foreshadowing.json"

    with pytest.raises(
        ForeshadowNotFoundError,
        match="Foreshadow item not found for id: fs-404",
    ):
        mark_foreshadow_resolved("fs-404", str(file_path))
