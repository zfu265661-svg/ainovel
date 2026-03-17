from __future__ import annotations

from typing import Any

from core.errors import is_missing_required_value
from core.storage import load_json, save_json


ForeshadowItem = dict[str, Any]
REQUIRED_FIELDS: tuple[str, ...] = (
    "id",
    "content",
    "introduced_in",
    "payoff_planned",
    "status",
)
DEFAULT_STATUS = "open"


class ForeshadowServiceError(RuntimeError):
    """Base exception for foreshadow tracking failures."""


class ForeshadowValidationError(ForeshadowServiceError):
    """Raised when foreshadow data is invalid."""


class ForeshadowNotFoundError(ForeshadowServiceError):
    """Raised when a foreshadow item cannot be found."""


def load_foreshadows(path: str = "data/foreshadowing.json") -> list[ForeshadowItem]:
    """Load foreshadow items from a UTF-8 encoded JSON file."""
    try:
        data = load_json(path)
    except FileNotFoundError:
        return []

    if not isinstance(data, list):
        raise ForeshadowValidationError(
            f"Foreshadow data file must contain a JSON array: {path}"
        )

    if not all(isinstance(item, dict) for item in data):
        raise ForeshadowValidationError(
            f"Each foreshadow entry must be a JSON object: {path}"
        )

    return data


def save_foreshadows(
    items: list[ForeshadowItem], path: str = "data/foreshadowing.json"
) -> None:
    """Save foreshadow items to a UTF-8 encoded JSON file."""
    save_json(path, items)


def add_foreshadow(
    item: ForeshadowItem, path: str = "data/foreshadowing.json"
) -> None:
    """Validate and append a foreshadow item."""
    normalized_item = _normalize_item(item)
    items = load_foreshadows(path)
    items.append(normalized_item)
    save_foreshadows(items, path)


def mark_foreshadow_resolved(
    item_id: str, path: str = "data/foreshadowing.json"
) -> None:
    """Mark the foreshadow item with the given id as resolved."""
    items = load_foreshadows(path)
    for item in items:
        if item.get("id") == item_id:
            item["status"] = "resolved"
            save_foreshadows(items, path)
            return

    raise ForeshadowNotFoundError(f"Foreshadow item not found for id: {item_id}")


def _normalize_item(item: ForeshadowItem) -> ForeshadowItem:
    if not isinstance(item, dict):
        raise ForeshadowValidationError("Foreshadow item must be a dictionary.")

    normalized_item = dict(item)
    if is_missing_required_value(normalized_item, "status"):
        normalized_item["status"] = DEFAULT_STATUS

    missing_fields = [
        field
        for field in REQUIRED_FIELDS
        if is_missing_required_value(normalized_item, field)
    ]
    if missing_fields:
        missing = ", ".join(missing_fields)
        raise ForeshadowValidationError(
            f"Foreshadow item is missing required field(s): {missing}"
        )

    return normalized_item
