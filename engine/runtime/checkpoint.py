from __future__ import annotations

from domain.models.checkpoint import Checkpoint
from domain.models.narrative_snapshot import NarrativeSnapshot
from infrastructure.persistence.json_repository import JsonProjectRepository


class CheckpointService:
    def __init__(self, repository: JsonProjectRepository) -> None:
        self.repository = repository

    def save_checkpoint(self, checkpoint: Checkpoint) -> str:
        return self.repository.save_checkpoint(
            checkpoint.project_id,
            checkpoint.chapter_id,
            checkpoint.to_dict(),
        )

    def restore_checkpoint(self, project_id: str, chapter_id: int, *, use_after: bool = False) -> NarrativeSnapshot:
        checkpoint = self.repository.load_checkpoint(project_id, chapter_id)
        key = "snapshot_after" if use_after else "snapshot_before"
        payload = checkpoint.get(key)
        if not isinstance(payload, dict):
            raise ValueError(f"Checkpoint is missing {key}.")
        snapshot = NarrativeSnapshot.from_dict(payload)
        self.repository.save_snapshot(snapshot)
        return snapshot
