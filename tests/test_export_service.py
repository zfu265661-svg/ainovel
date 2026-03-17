from __future__ import annotations

from pathlib import Path

import pytest

from core.export_service import export_chapter_text


def test_export_chapter_text_saves_to_default_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)

    exported_path = export_chapter_text(3, "Chapter 3 content")

    expected_path = tmp_path / "data" / "chapters" / "chapter_3.txt"
    assert exported_path == str(Path("data/chapters/chapter_3.txt"))
    assert expected_path.read_text(encoding="utf-8") == "Chapter 3 content"


def test_export_chapter_text_saves_to_custom_path(tmp_path: Path) -> None:
    custom_path = tmp_path / "exports" / "custom_chapter.txt"

    exported_path = export_chapter_text(7, "Custom content", path=str(custom_path))

    assert exported_path == str(custom_path)
    assert custom_path.read_text(encoding="utf-8") == "Custom content"


def test_export_chapter_text_raises_for_empty_text() -> None:
    with pytest.raises(ValueError, match="text content cannot be empty or whitespace only"):
        export_chapter_text(2, "   \n\t")
