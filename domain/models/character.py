from __future__ import annotations

from dataclasses import dataclass, field

from domain.models.base import JsonModel


@dataclass
class Character(JsonModel):
    id: str
    name: str
    role: str = ""
    traits: list[str] = field(default_factory=list)
    current_state: str = ""
    related_locations: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
