from __future__ import annotations

from typing import Any


LAYER_NAMES = ("mandatory", "compressed", "recent", "optional")


def empty_layers() -> dict[str, list[dict[str, Any]]]:
    return {name: [] for name in LAYER_NAMES}


def context_item(kind: str, item_id: str, title: str, source: str, payload: Any = None) -> dict[str, Any]:
    return {
        "kind": kind,
        "id": item_id,
        "title": title,
        "source": source,
        "payload": payload if payload is not None else {},
    }
