from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from domain.models.base import JsonModel


@dataclass
class ContextAudit(JsonModel):
    layers: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    budget: dict[str, int] = field(default_factory=dict)
    coverage: dict[str, list[str]] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


@dataclass
class ContextPackage(JsonModel):
    chapter_id: int
    layers: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    audit: ContextAudit = field(default_factory=ContextAudit)

    def all_items(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for layer_items in self.layers.values():
            items.extend(layer_items)
        return items
