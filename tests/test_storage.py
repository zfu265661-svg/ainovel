from __future__ import annotations

from pathlib import Path

import pytest

from core.storage import load_json, load_text, save_json, save_text


def test_save_and_load_json(tmp_path: Path) -> None:
    file_path = tmp_path / "nested" / "data.json"
    expected = {"title": "novel", "chapters": [1, 2, 3]}

    save_json(str(file_path), expected)

    assert load_json(str(file_path)) == expected


def test_save_and_load_text(tmp_path: Path) -> None:
    file_path = tmp_path / "nested" / "notes.txt"
    expected = "章节摘要"

    save_text(str(file_path), expected)

    assert load_text(str(file_path)) == expected


def test_missing_file_raises_clear_error(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing.json"

    with pytest.raises(FileNotFoundError, match="JSON file not found"):
        load_json(str(missing_path))

    with pytest.raises(FileNotFoundError, match="Text file not found"):
        load_text(str(tmp_path / "missing.txt"))


def test_invalid_json_raises_clear_error(tmp_path: Path) -> None:
    file_path = tmp_path / "broken.json"
    file_path.write_text("{invalid json}", encoding="utf-8")

    with pytest.raises(ValueError, match="Failed to parse JSON file"):
        load_json(str(file_path))
