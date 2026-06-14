from pathlib import Path

from domain.models.checkpoint import Checkpoint
from domain.models.context import ContextAudit, ContextPackage
from domain.models.narrative_snapshot import NarrativeSnapshot
from domain.models.pipeline import PipelineStageTrace, PipelineTrace
from engine.pipeline.stages import PIPELINE_STAGES
from engine.quality.consistency_checker import ConsistencyChecker
from engine.runtime.checkpoint import CheckpointService
from infrastructure.persistence.json_repository import JsonProjectRepository


def test_consistency_checker_finds_warning_and_trace_error(tmp_path):
    snapshot = NarrativeSnapshot.empty("demo")
    context = ContextPackage(
        chapter_id=2,
        layers={"mandatory": [], "compressed": [], "recent": [], "optional": []},
        audit=ContextAudit(
            coverage={
                "missing_entities": ["Alice"],
                "missing_locations": [],
                "active_threads_included": [],
                "foreshadows_included": [],
            }
        ),
    )
    trace = PipelineTrace(project_id="demo", chapter_id=2, status="failed", stages=[PipelineStageTrace(stage="prepare")])
    report = ConsistencyChecker().check(
        project_id="demo",
        chapter_id=2,
        snapshot=snapshot,
        chapter_plan={"characters": ["Alice"]},
        context=context,
        snapshot_update={"chapter_summary": ""},
        trace=trace,
        chapter_dir=Path(tmp_path),
    )

    codes = {finding.code for finding in report.findings}
    assert "previous_summary_missing" in codes
    assert "plan_character_missing_from_context" in codes
    assert "pipeline_trace_missing_stage" in codes


def test_checkpoint_service_saves_checkpoint(tmp_path):
    repo = JsonProjectRepository(tmp_path)
    service = CheckpointService(repo)
    path = service.save_checkpoint(
        Checkpoint(
            project_id="demo",
            chapter_id=1,
            checkpoint_id="cp1",
            snapshot_before={"project_id": "demo", "current_chapter": 0},
            snapshot_after={"project_id": "demo", "current_chapter": 1},
        )
    )
    assert Path(path).is_file()
    restored = service.restore_checkpoint("demo", 1)
    assert restored.current_chapter == 0


def test_pipeline_stages_include_required_order():
    assert PIPELINE_STAGES[0] == "prepare"
    assert PIPELINE_STAGES[-1] == "finish"
