from __future__ import annotations

from dataclasses import dataclass, field

from domain.models.base import JsonModel


@dataclass
class Location(JsonModel):
    id: str
    name: str
    description: str = ""
    current_state: str = ""
    related_characters: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
