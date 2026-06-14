from __future__ import annotations

from dataclasses import dataclass, field

from domain.models.base import JsonModel


@dataclass
class PlotThread(JsonModel):
    id: str
    title: str
    status: str = "unresolved"
    introduced_chapter: int = 0
    last_seen_chapter: int = 0
    next_expected_chapter: int | None = None
    related_characters: list[str] = field(default_factory=list)
    related_locations: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    risk: str = "ok"
