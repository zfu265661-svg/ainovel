from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from domain.models.base import JsonModel, utc_now_iso


@dataclass
class ChapterSummary(JsonModel):
    chapter_id: int
    title: str = ""
    summary: str = ""
    handoff: str = ""


@dataclass
class NarrativeSnapshot(JsonModel):
    project_id: str
    current_chapter: int = 0
    story_bible: dict[str, Any] = field(default_factory=dict)
    characters: list[dict[str, Any]] = field(default_factory=list)
    locations: list[dict[str, Any]] = field(default_factory=list)
    organizations: list[dict[str, Any]] = field(default_factory=list)
    plot_threads: list[dict[str, Any]] = field(default_factory=list)
    foreshadows: list[dict[str, Any]] = field(default_factory=list)
    scenes: list[dict[str, Any]] = field(default_factory=list)
    chapter_summaries: list[dict[str, Any]] = field(default_factory=list)
    last_updated: str = field(default_factory=utc_now_iso)

    @classmethod
    def empty(cls, project_id: str) -> "NarrativeSnapshot":
        return cls(
            project_id=project_id,
            story_bible={
                "premise": "",
                "genre": "",
                "themes": [],
                "world_rules": [],
                "style_guide": {},
                "taboos": [],
            },
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NarrativeSnapshot":
        return cls(
            project_id=str(data.get("project_id") or ""),
            current_chapter=int(data.get("current_chapter") or 0),
            story_bible=data.get("story_bible") if isinstance(data.get("story_bible"), dict) else {},
            characters=data.get("characters") if isinstance(data.get("characters"), list) else [],
            locations=data.get("locations") if isinstance(data.get("locations"), list) else [],
            organizations=data.get("organizations") if isinstance(data.get("organizations"), list) else [],
            plot_threads=data.get("plot_threads") if isinstance(data.get("plot_threads"), list) else [],
            foreshadows=data.get("foreshadows") if isinstance(data.get("foreshadows"), list) else [],
            scenes=data.get("scenes") if isinstance(data.get("scenes"), list) else [],
            chapter_summaries=data.get("chapter_summaries") if isinstance(data.get("chapter_summaries"), list) else [],
            last_updated=str(data.get("last_updated") or utc_now_iso()),
        )
