from __future__ import annotations

from dataclasses import dataclass, field

from domain.models.base import JsonModel, utc_now_iso


@dataclass
class NovelProject(JsonModel):
    project_id: str
    name: str
    description: str = ""
    current_chapter: int = 0
    target_chapters: int = 12
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    @classmethod
    def from_dict(cls, data: dict) -> "NovelProject":
        return cls(
            project_id=str(data.get("project_id") or data.get("id") or data.get("name") or ""),
            name=str(data.get("name") or data.get("project_id") or ""),
            description=str(data.get("description") or ""),
            current_chapter=int(data.get("current_chapter") or 0),
            target_chapters=int(data.get("target_chapters") or 12),
            created_at=str(data.get("created_at") or utc_now_iso()),
            updated_at=str(data.get("updated_at") or utc_now_iso()),
        )
