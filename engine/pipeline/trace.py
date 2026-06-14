from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from domain.models.base import utc_now_iso
from domain.models.pipeline import PipelineStageTrace, PipelineTrace


class TraceRecorder:
    def __init__(self, project_id: str, chapter_id: int) -> None:
        self.trace = PipelineTrace(project_id=project_id, chapter_id=chapter_id, status="running")

    @contextmanager
    def stage(self, name: str, inputs: list[str] | None = None) -> Iterator[PipelineStageTrace]:
        item = PipelineStageTrace(
            stage=name,
            status="running",
            started_at=utc_now_iso(),
            inputs=inputs or [],
        )
        self.trace.add_stage(item)
        try:
            yield item
            if item.status == "running":
                item.status = "success"
        except Exception as exc:
            item.status = "failed"
            item.errors.append(str(exc))
            raise
        finally:
            item.ended_at = utc_now_iso()

    def finish(self, status: str = "success") -> PipelineTrace:
        self.trace.status = status
        self.trace.ended_at = utc_now_iso()
        return self.trace
