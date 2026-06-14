from __future__ import annotations

from typing import Any

from domain.models.context import ContextAudit
from engine.context.context_layers import LAYER_NAMES


def build_context_audit(
    layers: dict[str, list[dict[str, Any]]],
    coverage: dict[str, list[str]],
    warnings: list[str],
    max_items: int,
) -> ContextAudit:
    selected_items = sum(len(layers.get(layer, [])) for layer in LAYER_NAMES)
    estimated_chars = sum(len(str(item)) for layer in LAYER_NAMES for item in layers.get(layer, []))
    return ContextAudit(
        layers={layer: layers.get(layer, []) for layer in LAYER_NAMES},
        budget={
            "max_items": max_items,
            "selected_items": selected_items,
            "estimated_chars": estimated_chars,
        },
        coverage=coverage,
        warnings=warnings,
    )
