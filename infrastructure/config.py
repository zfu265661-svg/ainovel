from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = PROJECT_ROOT / "data"
PROJECTS_ROOT = DATA_ROOT / "projects"
EXPORTS_ROOT = DATA_ROOT / "exports"


def ensure_data_dirs() -> None:
    PROJECTS_ROOT.mkdir(parents=True, exist_ok=True)
    EXPORTS_ROOT.mkdir(parents=True, exist_ok=True)
