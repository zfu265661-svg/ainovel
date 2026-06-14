from __future__ import annotations

from dataclasses import dataclass, field

from domain.models.base import JsonModel, utc_now_iso


@dataclass
class ConsistencyFinding(JsonModel):
    level: str
    code: str
    message: str
    related_stage: str = ""
    related_items: list[str] = field(default_factory=list)


@dataclass
class ConsistencyReport(JsonModel):
    project_id: str
    chapter_id: int
    findings: list[ConsistencyFinding] = field(default_factory=list)
    generated_at: str = field(default_factory=utc_now_iso)

    @property
    def status(self) -> str:
        return "error" if any(item.level == "error" for item in self.findings) else "ok"
