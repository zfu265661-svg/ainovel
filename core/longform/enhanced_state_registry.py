from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EnhancedStateTarget:
    """Read-only enhanced-state target used by status and inspection diagnostics."""

    name: str
    path_key: str
    item_key: str | None = None


ENHANCED_STATE_TARGETS: tuple[EnhancedStateTarget, ...] = (
    EnhancedStateTarget("story_bible", "story_bible_json"),
    EnhancedStateTarget("plot_threads", "plot_threads_json", "threads"),
    EnhancedStateTarget("locations", "locations_json", "locations"),
    EnhancedStateTarget("organizations", "organizations_json", "organizations"),
    EnhancedStateTarget("style_guide", "style_guide_json"),
    EnhancedStateTarget("scenes", "scenes_json", "scenes"),
)


def get_enhanced_state_targets() -> tuple[EnhancedStateTarget, ...]:
    return ENHANCED_STATE_TARGETS
