from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.errors import parse_json_file_text


JsonData = dict[str, Any] | list[Any]


def load_json(path: str) -> JsonData:
    """Load JSON data from a UTF-8 encoded file."""
    file_path = Path(path)
    try:
        content = file_path.read_text(encoding="utf-8-sig")
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"JSON file not found: {file_path}") from exc

    try:
        data: Any = parse_json_file_text(content)
    except ValueError as exc:
        raise ValueError(f"Failed to parse JSON file {file_path}: {exc}") from exc

    if not isinstance(data, (dict, list)):
        raise ValueError(f"JSON file must contain an object or array: {file_path}")

    return data


def save_json(path: str, data: JsonData) -> None:
    """Save JSON data to a UTF-8 encoded file, creating parent directories when needed."""
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_text(path: str) -> str:
    """Load plain text from a UTF-8 encoded file."""
    file_path = Path(path)
    try:
        return file_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Text file not found: {file_path}") from exc


def save_text(path: str, content: str) -> None:
    """Save plain text to a UTF-8 encoded file, creating parent directories when needed."""
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")
