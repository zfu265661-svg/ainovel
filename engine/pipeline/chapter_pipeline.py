from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from domain.models.base import utc_now_iso
from domain.models.checkpoint import Checkpoint
from domain.models.narrative_snapshot import NarrativeSnapshot
from engine.context.context_assembler import ContextAssembler
from engine.pipeline.trace import TraceRecorder
from engine.quality.consistency_checker import ConsistencyChecker
from engine.runtime.checkpoint import CheckpointService
from infrastructure.llm.client import DeterministicLLMClient
from infrastructure.llm.prompts import render_chapter_plan
from infrastructure.persistence.json_repository import JsonProjectRepository


class ChapterPipeline:
    def __init__(
        self,
        repository: JsonProjectRepository,
        llm_client: DeterministicLLMClient | None = None,
        context_assembler: ContextAssembler | None = None,
        consistency_checker: ConsistencyChecker | None = None,
    ) -> None:
        self.repository = repository
        self.llm = llm_client or DeterministicLLMClient()
        self.context_assembler = context_assembler or ContextAssembler()
        self.consistency_checker = consistency_checker or ConsistencyChecker()
        self.checkpoints = CheckpointService(repository)

    def run(
        self,
        project_id: str,
        chapter_id: int,
        *,
        dry_run: bool = False,
        review_before_commit: bool = False,
    ) -> dict[str, Any]:
        trace = TraceRecorder(project_id, chapter_id)
        project = None
        snapshot = None
        snapshot_before: dict[str, Any] = {}
        snapshot_after: dict[str, Any] = {}
        chapter_plan: dict[str, Any] = {}
        context = None
        draft = ""
        rewrite = ""
        summary = ""
        snapshot_update: dict[str, Any] = {}
        report = None
        checkpoint_path = ""
        trace_path = ""
        audit_path = ""
        report_path = ""

        try:
            with trace.stage("prepare", ["project_id", "chapter_id"]) as stage:
                project = self.repository.load_project(project_id)
                self.repository.chapter_dir(project_id, chapter_id).mkdir(parents=True, exist_ok=True)
                stage.outputs.append("chapter_workspace_ready")

            with trace.stage("load_snapshot", ["snapshot.json"]) as stage:
                snapshot = self.repository.load_snapshot(project_id)
                snapshot_before = snapshot.to_dict()
                stage.outputs.append("snapshot_loaded")

            with trace.stage("build_chapter_plan", ["project", "snapshot"]) as stage:
                previous = self._previous_summary(snapshot, chapter_id)
                chapter_plan = render_chapter_plan(
                    project.name,
                    chapter_id,
                    str(previous.get("handoff") or "") if previous else "",
                )
                self._seed_plan_from_snapshot(chapter_plan, snapshot)
                self.repository.save_chapter_text(project_id, chapter_id, "plan.md", self._render_plan(chapter_plan))
                stage.outputs.append("plan.md")

            with trace.stage("assemble_context", ["chapter_plan", "snapshot"]) as stage:
                context = self.context_assembler.assemble(snapshot=snapshot, chapter_id=chapter_id, chapter_plan=chapter_plan)
                audit_path = self.repository.save_chapter_json(project_id, chapter_id, "context_audit.json", context.audit.to_dict())
                stage.outputs.extend(["context_package", audit_path])
                stage.warnings.extend(context.audit.warnings)

            with trace.stage("draft", ["chapter_plan", "context"]) as stage:
                draft = self.llm.draft(chapter_plan, context)
                self.repository.save_chapter_text(project_id, chapter_id, "draft.md", draft)
                stage.outputs.append("draft.md")

            with trace.stage("rewrite", ["draft"]) as stage:
                rewrite = self.llm.rewrite(draft, chapter_plan)
                self.repository.save_chapter_text(project_id, chapter_id, "rewrite.md", rewrite)
                stage.outputs.append("rewrite.md")

            with trace.stage("summarize", ["rewrite"]) as stage:
                summary = self.llm.summarize(rewrite, chapter_plan)
                self.repository.save_chapter_text(project_id, chapter_id, "summary.md", summary)
                stage.outputs.append("summary.md")

            with trace.stage("suggest_updates", ["summary", "chapter_plan"]) as stage:
                snapshot_update = self.llm.suggest_updates(chapter_plan, summary)
                self.repository.save_chapter_json(project_id, chapter_id, "snapshot_update.json", snapshot_update)
                stage.outputs.append("snapshot_update.json")

            with trace.stage("consistency_check", ["snapshot", "context", "snapshot_update"]) as stage:
                report = self.consistency_checker.check(
                    project_id=project_id,
                    chapter_id=chapter_id,
                    snapshot=snapshot,
                    chapter_plan=chapter_plan,
                    context=context,
                    snapshot_update=snapshot_update,
                    trace=trace.trace,
                    chapter_dir=self.repository.chapter_dir(project_id, chapter_id),
                )
                report_path = self.repository.save_chapter_json(project_id, chapter_id, "consistency_report.json", report.to_dict())
                stage.outputs.append(report_path)
                stage.warnings.extend(item.code for item in report.findings if item.level == "warning")
                stage.errors.extend(item.code for item in report.findings if item.level == "error")

            with trace.stage("review_gate", ["consistency_report"]) as stage:
                if review_before_commit:
                    stage.warnings.append("review_before_commit_enabled")
                    stage.outputs.append("pending_review")
                else:
                    stage.outputs.append("auto_approved")

            with trace.stage("commit_snapshot", ["snapshot_update"]) as stage:
                snapshot_after_model = self._apply_snapshot_update(snapshot, chapter_id, chapter_plan, snapshot_update)
                snapshot_after = snapshot_after_model.to_dict()
                if dry_run:
                    stage.warnings.append("dry_run_no_snapshot_commit")
                elif review_before_commit:
                    stage.warnings.append("review_required_no_snapshot_commit")
                else:
                    self.repository.save_snapshot(snapshot_after_model)
                    project.current_chapter = max(project.current_chapter, chapter_id)
                    project.updated_at = utc_now_iso()
                    self.repository.save_project(project)
                    stage.outputs.append("snapshot.json")

            with trace.stage("save_outputs", ["trace", "audit", "report"]) as stage:
                trace_path = self.repository.save_chapter_json(project_id, chapter_id, "trace.json", trace.trace.to_dict())
                stage.outputs.extend([trace_path, audit_path, report_path])

            with trace.stage("checkpoint", ["snapshot_before", "snapshot_after"]) as stage:
                checkpoint = Checkpoint(
                    project_id=project_id,
                    chapter_id=chapter_id,
                    checkpoint_id=f"checkpoint_ch{chapter_id:03d}",
                    snapshot_before=snapshot_before,
                    snapshot_after=snapshot_after,
                    trace_path=trace_path,
                    consistency_report_path=report_path,
                )
                checkpoint_path = self.checkpoints.save_checkpoint(checkpoint)
                stage.outputs.append(checkpoint_path)

            with trace.stage("finish", ["checkpoint"]) as stage:
                stage.outputs.append("pipeline_finished")
                final_status = "pending_review" if review_before_commit else "dry_run" if dry_run else "success"

            final_trace = trace.finish(final_status)
            trace_path = self.repository.save_chapter_json(project_id, chapter_id, "trace.json", final_trace.to_dict())
            return {
                "project_id": project_id,
                "chapter_id": chapter_id,
                "status": final_trace.status,
                "trace_path": trace_path,
                "context_audit_path": audit_path,
                "consistency_report_path": report_path,
                "checkpoint_path": checkpoint_path,
                "dry_run": dry_run,
                "review_before_commit": review_before_commit,
            }
        except Exception:
            final_trace = trace.finish("failed")
            self.repository.save_chapter_json(project_id, chapter_id, "trace.json", final_trace.to_dict())
            raise

    @staticmethod
    def _render_plan(chapter_plan: dict[str, Any]) -> str:
        lines = [f"# {chapter_plan.get('title')}", "", str(chapter_plan.get("goal") or "")]
        for key in ("characters", "locations", "organizations", "plot_threads", "foreshadows"):
            values = chapter_plan.get(key) if isinstance(chapter_plan.get(key), list) else []
            lines.append("")
            lines.append(f"{key}: {', '.join(str(item) for item in values) or 'none'}")
        return "\n".join(lines).strip() + "\n"

    @staticmethod
    def _previous_summary(snapshot: NarrativeSnapshot, chapter_id: int) -> dict[str, Any] | None:
        for item in reversed(snapshot.chapter_summaries):
            if item.get("chapter_id") == chapter_id - 1:
                return item
        return None

    @staticmethod
    def _seed_plan_from_snapshot(chapter_plan: dict[str, Any], snapshot: NarrativeSnapshot) -> None:
        if snapshot.characters:
            chapter_plan["characters"] = [str(snapshot.characters[0].get("name") or snapshot.characters[0].get("id"))]
        if snapshot.locations:
            chapter_plan["locations"] = [str(snapshot.locations[0].get("name") or snapshot.locations[0].get("id"))]
        if snapshot.organizations:
            chapter_plan["organizations"] = [str(snapshot.organizations[0].get("name") or snapshot.organizations[0].get("id"))]
        chapter_plan["plot_threads"] = [
            str(item.get("id") or item.get("title"))
            for item in snapshot.plot_threads
            if item.get("status") in ("active", "unresolved")
        ]
        chapter_plan["foreshadows"] = [
            str(item.get("id") or item.get("title"))
            for item in snapshot.foreshadows
            if item.get("status") == "active"
        ]

    @staticmethod
    def _apply_snapshot_update(
        snapshot: NarrativeSnapshot,
        chapter_id: int,
        chapter_plan: dict[str, Any],
        snapshot_update: dict[str, Any],
    ) -> NarrativeSnapshot:
        updated = NarrativeSnapshot.from_dict(deepcopy(snapshot.to_dict()))
        updated.current_chapter = max(updated.current_chapter, chapter_id)
        updated.last_updated = utc_now_iso()
        updated.chapter_summaries = [
            item for item in updated.chapter_summaries if item.get("chapter_id") != chapter_id
        ]
        updated.chapter_summaries.append(
            {
                "chapter_id": chapter_id,
                "title": chapter_plan.get("title") or f"Chapter {chapter_id}",
                "summary": snapshot_update.get("chapter_summary") or "",
                "handoff": snapshot_update.get("handoff") or "",
            }
        )
        for thread in updated.plot_threads:
            if thread.get("status") in ("active", "unresolved"):
                thread["last_seen_chapter"] = chapter_id
                thread["risk"] = "ok"
        for item in updated.foreshadows:
            expected = item.get("expected_payoff_chapter")
            if item.get("status") == "active" and isinstance(expected, int) and expected < chapter_id:
                item["risk"] = "overdue"
        return updated
