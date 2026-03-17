from pathlib import Path

import pytest

from core import prompt_loader


def test_load_prompt_reads_prompt_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    prompt_dir = tmp_path / "prompts"
    prompt_dir.mkdir()
    prompt_file = prompt_dir / "outline.txt"
    prompt_file.write_text("prompt content", encoding="utf-8")
    monkeypatch.setattr(prompt_loader, "PROMPTS_DIR", prompt_dir)

    result = prompt_loader.load_prompt("outline.txt")

    assert result == "prompt content"


def test_load_prompt_raises_for_missing_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    prompt_dir = tmp_path / "prompts"
    prompt_dir.mkdir()
    monkeypatch.setattr(prompt_loader, "PROMPTS_DIR", prompt_dir)

    with pytest.raises(FileNotFoundError, match="missing.txt"):
        prompt_loader.load_prompt("missing.txt")
