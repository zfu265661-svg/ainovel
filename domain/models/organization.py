from __future__ import annotations

from dataclasses import dataclass, field

from domain.models.base import JsonModel


@dataclass
class Organization(JsonModel):
    id: str
    name: str
    description: str = ""
    goals: list[str] = field(default_factory=list)
    members: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
