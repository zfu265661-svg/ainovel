from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from domain.models.base import JsonModel, utc_now_iso


@dataclass
class Checkpoint(JsonModel):
    project_id: str
    chapter_id: int
    checkpoint_id: str
    created_at: str = field(default_factory=utc_now_iso)
    snapshot_before: dict[str, Any] = field(default_factory=dict)
    snapshot_after: dict[str, Any] = field(default_factory=dict)
    trace_path: str = ""
    consistency_report_path: str = ""
    status: str = "created"
