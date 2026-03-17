from __future__ import annotations

from pathlib import Path

import pytest

from core.character_service import (
    CharacterConflictError,
    CharacterValidationError,
    add_character,
    get_character_by_name,
    load_characters,
    save_characters,
)


def test_save_and_load_characters(tmp_path: Path) -> None:
    file_path = tmp_path / "characters.json"
    expected = [
        {"name": "Lin Yue", "role": "protagonist", "trait": "calm"},
        {"name": "Su He", "role": "mentor"},
    ]

    save_characters(expected, str(file_path))

    assert load_characters(str(file_path)) == expected


def test_get_character_by_name_returns_character(tmp_path: Path) -> None:
    file_path = tmp_path / "characters.json"
    save_characters(
        [
            {"name": "Lin Yue", "role": "protagonist"},
            {"name": "Su He", "role": "mentor"},
        ],
        str(file_path),
    )

    result = get_character_by_name("Su He", str(file_path))

    assert result == {"name": "Su He", "role": "mentor"}


def test_add_character_raises_for_missing_required_fields(tmp_path: Path) -> None:
    file_path = tmp_path / "characters.json"

    with pytest.raises(
        CharacterValidationError,
        match="missing required field\\(s\\): role",
    ):
        add_character({"name": "Lin Yue"}, str(file_path))


def test_add_character_raises_for_duplicate_name(tmp_path: Path) -> None:
    file_path = tmp_path / "characters.json"
    add_character({"name": "Lin Yue", "role": "protagonist"}, str(file_path))

    with pytest.raises(
        CharacterConflictError,
        match="Character with name 'Lin Yue' already exists",
    ):
        add_character({"name": "Lin Yue", "role": "rival"}, str(file_path))
