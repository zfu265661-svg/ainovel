from __future__ import annotations

from pathlib import Path
from typing import Any

from domain.models.context import ContextPackage
from domain.models.narrative_snapshot import NarrativeSnapshot
from domain.models.pipeline import PipelineTrace
from domain.models.quality import ConsistencyFinding, ConsistencyReport
from engine.pipeline.stages import PIPELINE_STAGES


class ConsistencyChecker:
    def check(
        self,
        *,
        project_id: str,
        chapter_id: int,
        snapshot: NarrativeSnapshot,
        chapter_plan: dict[str, Any],
        context: ContextPackage,
        snapshot_update: dict[str, Any],
        trace: PipelineTrace,
        chapter_dir: Path,
    ) -> ConsistencyReport:
        findings: list[ConsistencyFinding] = []
        coverage = context.audit.coverage

        if chapter_id > 1 and self._previous_summary(snapshot, chapter_id) is None:
            findings.append(self._finding("warning", "previous_summary_missing", "Previous chapter summary is missing.", "assemble_context"))
        previous = self._previous_summary(snapshot, chapter_id)
        if chapter_id > 1 and previous is not None and not str(previous.get("handoff") or "").strip():
            findings.append(self._finding("warning", "previous_handoff_missing", "Previous chapter handoff is missing.", "assemble_context"))

        for name in coverage.get("missing_entities", []):
            findings.append(self._finding("warning", "plan_character_missing_from_context", f"Plan character not in context: {name}", "assemble_context", [name]))
        for name in coverage.get("missing_locations", []):
            findings.append(self._finding("warning", "plan_location_missing_from_context", f"Plan location not in context: {name}", "assemble_context", [name]))

        for item in snapshot.plot_threads:
            if item.get("status") in ("active", "unresolved") and str(item.get("id")) not in coverage.get("active_threads_included", []):
                findings.append(self._finding("error", "active_plot_thread_missing_from_context", "Active plot thread missing from context.", "assemble_context", [str(item.get("id"))]))
            if item.get("status") == "active" and int(item.get("last_seen_chapter") or 0) < max(0, chapter_id - 3):
                findings.append(self._finding("warning", "active_plot_thread_stale", "Active plot thread has not appeared recently.", "consistency_check", [str(item.get("id"))]))

        for item in snapshot.foreshadows:
            if item.get("status") == "active" and str(item.get("id")) not in coverage.get("foreshadows_included", []):
                findings.append(self._finding("error", "active_foreshadow_missing_from_context", "Active foreshadow missing from context.", "assemble_context", [str(item.get("id"))]))
            expected = item.get("expected_payoff_chapter")
            if item.get("status") == "active" and isinstance(expected, int) and expected < chapter_id:
                findings.append(self._finding("warning", "foreshadow_overdue", "Foreshadow is overdue for payoff.", "consistency_check", [str(item.get("id"))]))

        self._check_blank_snapshot_update(snapshot_update, findings)
        self._check_character_conflicts(snapshot_update, findings)
        self._check_trace_stages(trace, findings)
        self._check_output_files(chapter_dir, findings)

        return ConsistencyReport(project_id=project_id, chapter_id=chapter_id, findings=findings)

    @staticmethod
    def _previous_summary(snapshot: NarrativeSnapshot, chapter_id: int) -> dict[str, Any] | None:
        for item in snapshot.chapter_summaries:
            if item.get("chapter_id") == chapter_id - 1:
                return item
        return None

    @staticmethod
    def _check_blank_snapshot_update(update: dict[str, Any], findings: list[ConsistencyFinding]) -> None:
        for key, value in update.items():
            if value == "" or value == [] or value == {}:
                findings.append(ConsistencyFinding("warning", "snapshot_update_blank_field", f"Snapshot update field is blank: {key}", "suggest_updates", [key]))

    @staticmethod
    def _check_character_conflicts(update: dict[str, Any], findings: list[ConsistencyFinding]) -> None:
        seen: dict[str, str] = {}
        updates = update.get("character_updates")
        if not isinstance(updates, list):
            return
        for item in updates:
            if not isinstance(item, dict):
                continue
            target = str(item.get("target") or "").strip()
            content = str(item.get("content") or "").strip()
            if not target:
                continue
            if target in seen and seen[target] != content:
                findings.append(ConsistencyFinding("error", "character_state_conflict", f"Conflicting updates for character: {target}", "suggest_updates", [target]))
            seen[target] = content

    @staticmethod
    def _check_trace_stages(trace: PipelineTrace, findings: list[ConsistencyFinding]) -> None:
        present = {stage.stage for stage in trace.stages}
        required_stages = PIPELINE_STAGES
        if trace.status == "running":
            current_index = PIPELINE_STAGES.index("consistency_check") + 1
            required_stages = PIPELINE_STAGES[:current_index]
        for required in required_stages:
            if required not in present and required != "finish":
                findings.append(ConsistencyFinding("error", "pipeline_trace_missing_stage", f"Pipeline trace missing stage: {required}", "consistency_check", [required]))

    @staticmethod
    def _check_output_files(chapter_dir: Path, findings: list[ConsistencyFinding]) -> None:
        for name in ("plan.md", "draft.md", "rewrite.md", "summary.md"):
            if not (chapter_dir / name).is_file():
                findings.append(ConsistencyFinding("warning", "chapter_output_missing", f"Chapter output file missing: {name}", "save_outputs", [name]))

    @staticmethod
    def _finding(level: str, code: str, message: str, stage: str, items: list[str] | None = None) -> ConsistencyFinding:
        return ConsistencyFinding(level=level, code=code, message=message, related_stage=stage, related_items=items or [])
