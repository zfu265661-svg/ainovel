from __future__ import annotations

from engine.runtime.engine_runner import build_default_pipeline


def run_chapter(project_id: str, chapter_id: int, dry_run: bool = False, review_before_commit: bool = False) -> dict:
    pipeline = build_default_pipeline()
    return pipeline.run(
        project_id=project_id,
        chapter_id=chapter_id,
        dry_run=dry_run,
        review_before_commit=review_before_commit,
    )
