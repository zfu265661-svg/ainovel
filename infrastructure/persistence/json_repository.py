from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from domain.models.narrative_snapshot import NarrativeSnapshot
from domain.models.project import NovelProject
from infrastructure.config import PROJECTS_ROOT, ensure_data_dirs


class JsonProjectRepository:
    def __init__(self, projects_root: Path | str | None = None) -> None:
        root = projects_root or os.environ.get("NOVEL_ENGINE_PROJECTS_ROOT") or PROJECTS_ROOT
        self.projects_root = Path(root)
        ensure_data_dirs()
        self.projects_root.mkdir(parents=True, exist_ok=True)

    def list_projects(self) -> list[dict[str, Any]]:
        projects: list[dict[str, Any]] = []
        for path in sorted(self.projects_root.glob("*/project.json")):
            try:
                projects.append(self._read_json(path))
            except Exception:
                projects.append({"project_id": path.parent.name, "name": path.parent.name, "status": "unreadable"})
        return projects

    def project_dir(self, project_id: str) -> Path:
        return self.projects_root / self._safe_id(project_id)

    def chapters_dir(self, project_id: str) -> Path:
        return self.project_dir(project_id) / "chapters"

    def chapter_dir(self, project_id: str, chapter_id: int) -> Path:
        return self.chapters_dir(project_id) / f"ch{chapter_id:03d}"

    def checkpoints_dir(self, project_id: str) -> Path:
        return self.project_dir(project_id) / "checkpoints"

    def create_project_dirs(self, project_id: str) -> None:
        self.project_dir(project_id).mkdir(parents=True, exist_ok=True)
        self.chapters_dir(project_id).mkdir(parents=True, exist_ok=True)
        self.checkpoints_dir(project_id).mkdir(parents=True, exist_ok=True)

    def save_project(self, project: NovelProject) -> None:
        self.create_project_dirs(project.project_id)
        self._write_json(self.project_dir(project.project_id) / "project.json", project.to_dict())

    def load_project(self, project_id: str) -> NovelProject:
        data = self._read_json(self.project_dir(project_id) / "project.json")
        return NovelProject.from_dict(data)

    def save_snapshot(self, snapshot: NarrativeSnapshot) -> None:
        self.create_project_dirs(snapshot.project_id)
        self._write_json(self.project_dir(snapshot.project_id) / "snapshot.json", snapshot.to_dict())

    def load_snapshot(self, project_id: str) -> NarrativeSnapshot:
        path = self.project_dir(project_id) / "snapshot.json"
        if not path.is_file():
            snapshot = NarrativeSnapshot.empty(project_id)
            self.save_snapshot(snapshot)
            return snapshot
        return NarrativeSnapshot.from_dict(self._read_json(path))

    def save_chapter_text(self, project_id: str, chapter_id: int, name: str, text: str) -> str:
        chapter_dir = self.chapter_dir(project_id, chapter_id)
        chapter_dir.mkdir(parents=True, exist_ok=True)
        path = chapter_dir / name
        path.write_text(text, encoding="utf-8")
        return str(path)

    def read_chapter_text(self, project_id: str, chapter_id: int, name: str) -> str:
        return (self.chapter_dir(project_id, chapter_id) / name).read_text(encoding="utf-8")

    def save_chapter_json(self, project_id: str, chapter_id: int, name: str, payload: dict[str, Any]) -> str:
        chapter_dir = self.chapter_dir(project_id, chapter_id)
        chapter_dir.mkdir(parents=True, exist_ok=True)
        path = chapter_dir / name
        self._write_json(path, payload)
        return str(path)

    def load_chapter_json(self, project_id: str, chapter_id: int, name: str) -> dict[str, Any]:
        return self._read_json(self.chapter_dir(project_id, chapter_id) / name)

    def save_checkpoint(self, project_id: str, chapter_id: int, payload: dict[str, Any]) -> str:
        self.create_project_dirs(project_id)
        path = self.checkpoints_dir(project_id) / f"checkpoint_ch{chapter_id:03d}.json"
        self._write_json(path, payload)
        return str(path)

    def load_checkpoint(self, project_id: str, chapter_id: int) -> dict[str, Any]:
        path = self.checkpoints_dir(project_id) / f"checkpoint_ch{chapter_id:03d}.json"
        return self._read_json(path)

    def list_checkpoints(self, project_id: str) -> list[dict[str, Any]]:
        checkpoints: list[dict[str, Any]] = []
        for path in sorted(self.checkpoints_dir(project_id).glob("checkpoint_ch*.json")):
            data = self._read_json(path)
            data["path"] = str(path)
            checkpoints.append(data)
        return checkpoints

    def list_chapters(self, project_id: str) -> list[dict[str, Any]]:
        chapters = []
        chapters_dir = self.chapters_dir(project_id)
        if not chapters_dir.is_dir():
            return chapters
        for path in sorted(chapters_dir.glob("ch*")):
            if not path.is_dir():
                continue
            chapter_id = int(path.name[2:]) if path.name[2:].isdigit() else 0
            chapters.append(
                {
                    "chapter_id": chapter_id,
                    "chapter_dir": str(path),
                    "has_trace": (path / "trace.json").is_file(),
                    "has_context_audit": (path / "context_audit.json").is_file(),
                    "has_consistency_report": (path / "consistency_report.json").is_file(),
                    "has_summary": (path / "summary.md").is_file(),
                }
            )
        return chapters

    @staticmethod
    def _safe_id(value: str) -> str:
        safe = "".join(ch for ch in str(value).strip() if ch.isalnum() or ch in ("-", "_"))
        if not safe:
            raise ValueError("project_id must contain at least one safe character.")
        return safe

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"JSON object expected: {path}")
        return data

    @staticmethod
    def _write_json(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
