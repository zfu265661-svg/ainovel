from __future__ import annotations

from pathlib import Path
from typing import Any

from core.errors import is_missing_required_value
from core.storage import load_json, save_json


Character = dict[str, Any]
REQUIRED_FIELDS: tuple[str, ...] = ("name", "role")
DEFAULT_PATH = "data/characters.json"


class CharacterServiceError(RuntimeError):
    """Base exception for character management failures."""


class CharacterValidationError(CharacterServiceError):
    """Raised when character data is invalid."""


class CharacterConflictError(CharacterServiceError):
    """Raised when adding a character that already exists."""


def load_characters(path: str = DEFAULT_PATH) -> list[Character]:
    """Load all characters from a UTF-8 encoded JSON file."""
    resolved_path = _resolve_characters_path(path)
    try:
        data = load_json(resolved_path)
    except FileNotFoundError:
        return []

    if not isinstance(data, list):
        raise CharacterValidationError(
            f"Character data file must contain a JSON array: {resolved_path}"
        )

    if not all(isinstance(item, dict) for item in data):
        raise CharacterValidationError(
            f"Each character entry must be a JSON object: {resolved_path}"
        )

    return data


def save_characters(
    characters: list[Character], path: str = DEFAULT_PATH
) -> None:
    """Save all characters to a UTF-8 encoded JSON file."""
    save_json(_resolve_characters_path(path), characters)


def add_character(character: Character, path: str = DEFAULT_PATH) -> None:
    """Add a new character after validation and duplicate-name checks."""
    _validate_character(character)

    characters = load_characters(path)
    if _find_character_by_name(characters, str(character["name"])) is not None:
        raise CharacterConflictError(
            f"Character with name '{character['name']}' already exists."
        )

    characters.append(character)
    save_characters(characters, path)


def get_character_by_name(
    name: str, path: str = DEFAULT_PATH
) -> Character | None:
    """Return the first character whose name matches exactly."""
    return _find_character_by_name(load_characters(path), name)


def _resolve_characters_path(path: str) -> str:
    candidate = Path(path)
    if candidate.suffix.lower() == ".json":
        return str(candidate)
    return str(candidate / "characters.json")


def _validate_character(character: Character) -> None:
    if not isinstance(character, dict):
        raise CharacterValidationError("Character must be a dictionary.")

    missing_fields = [
        field for field in REQUIRED_FIELDS if is_missing_required_value(character, field)
    ]
    if missing_fields:
        missing = ", ".join(missing_fields)
        raise CharacterValidationError(
            f"Character is missing required field(s): {missing}"
        )


def _find_character_by_name(
    characters: list[Character],
    name: str,
) -> Character | None:
    for character in characters:
        if character.get("name") == name:
            return character
    return None
