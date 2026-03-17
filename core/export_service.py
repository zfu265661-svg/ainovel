from __future__ import annotations

from pathlib import Path

from core.storage import save_text


def export_chapter_text(chapter_no: int, text: str, path: str | None = None) -> str:
    """Export chapter text to a local UTF-8 text file and return the final path."""
    if not text.strip():
        raise ValueError(
            f"Chapter {chapter_no} export failed: text content cannot be empty or whitespace only."
        )

    file_path = Path(path) if path is not None else Path("data/chapters") / f"chapter_{chapter_no}.txt"
    save_text(str(file_path), text)
    return str(file_path)
