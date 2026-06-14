from __future__ import annotations

from dataclasses import dataclass, field

from domain.models.base import JsonModel, utc_now_iso


@dataclass
class Chapter(JsonModel):
    chapter_id: int
    title: str = ""
    status: str = "planned"
    plan: dict = field(default_factory=dict)
    summary: str = ""
    handoff: str = ""
    output_paths: dict[str, str] = field(default_factory=dict)
    updated_at: str = field(default_factory=utc_now_iso)

    @property
    def slug(self) -> str:
        return f"ch{self.chapter_id:03d}"
