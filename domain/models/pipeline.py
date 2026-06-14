from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from domain.models.base import JsonModel, utc_now_iso


@dataclass
class PipelineStageTrace(JsonModel):
    stage: str
    status: str = "pending"
    started_at: str = ""
    ended_at: str = ""
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class PipelineTrace(JsonModel):
    project_id: str
    chapter_id: int
    stages: list[PipelineStageTrace] = field(default_factory=list)
    status: str = "pending"
    started_at: str = field(default_factory=utc_now_iso)
    ended_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_stage(self, stage: PipelineStageTrace) -> None:
        self.stages.append(stage)
