from __future__ import annotations

from dataclasses import dataclass, field

from domain.models.base import JsonModel


@dataclass
class Scene(JsonModel):
    id: str
    chapter_id: int
    title: str = ""
    goal: str = ""
    summary: str = ""
    location_id: str = ""
    character_ids: list[str] = field(default_factory=list)
    status: str = "planned"
