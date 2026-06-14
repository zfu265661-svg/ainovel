from pathlib import Path

from domain.models.narrative_snapshot import NarrativeSnapshot
from domain.models.project import NovelProject
from engine.pipeline.chapter_pipeline import ChapterPipeline
from infrastructure.persistence.json_repository import JsonProjectRepository


def test_chapter_pipeline_generates_artifacts(tmp_path):
    repo = JsonProjectRepository(tmp_path)
    repo.save_project(NovelProject(project_id="demo", name="Demo"))
    snapshot = NarrativeSnapshot.empty("demo")
    snapshot.characters.append({"id": "c1", "name": "Protagonist"})
    snapshot.locations.append({"id": "l1", "name": "Starting Place"})
    snapshot.plot_threads.append({"id": "main-thread", "title": "Main", "status": "active", "last_seen_chapter": 0})
    snapshot.foreshadows.append({"id": "opening-hook", "title": "Hook", "status": "active", "expected_payoff_chapter": 3})
    repo.save_snapshot(snapshot)

    result = ChapterPipeline(repo).run("demo", 1)

    assert result["status"] == "success"
    chapter_dir = repo.chapter_dir("demo", 1)
    for name in ("plan.md", "draft.md", "rewrite.md", "summary.md", "trace.json", "context_audit.json", "consistency_report.json"):
        assert (chapter_dir / name).is_file()
    assert Path(result["checkpoint_path"]).is_file()
    assert repo.load_snapshot("demo").current_chapter == 1
    assert repo.load_project("demo").current_chapter == 1
