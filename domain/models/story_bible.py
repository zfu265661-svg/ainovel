from __future__ import annotations

from dataclasses import dataclass, field

from domain.models.base import JsonModel


@dataclass
class StoryBible(JsonModel):
    premise: str = ""
    genre: str = ""
    themes: list[str] = field(default_factory=list)
    world_rules: list[str] = field(default_factory=list)
    style_guide: dict = field(default_factory=dict)
    taboos: list[str] = field(default_factory=list)
