from __future__ import annotations

from dataclasses import dataclass, field

from domain.models.base import JsonModel


@dataclass
class Foreshadow(JsonModel):
    id: str
    title: str
    status: str = "active"
    planted_chapter: int = 0
    expected_payoff_chapter: int | None = None
    payoff_chapter: int | None = None
    risk: str = "ok"
    notes: list[str] = field(default_factory=list)
