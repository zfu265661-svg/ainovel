# Architecture

## Goal

This repository is a project-driven long-form novel writing agent kernel. Phase 3 MVP keeps the stable Phase 1 / Phase 2 workflow and adds the first layer of full Agent Kernel structure.

The default path remains:

`plan -> draft -> rewrite -> summarize -> suggest -> review -> consistency_check -> commit`

The long-term target is:

`idea -> project brief -> story bible -> outline -> volume plan -> arc plan -> chapter plan -> scene plan -> draft -> rewrite -> edit -> continuity check -> style check -> review -> commit -> export`

## Current Layers

- CLI: `phase1_cli.py` and `phase2_cli.py`
- Workflow orchestration: `core/workflow_service.py`, `core/longform/chapter_runner_service.py`, `core/longform/serial_workflow_service.py`
- Generation services: outline, volume, chapter, draft, rewrite, summary, suggestion
- Formal state: `characters.json`, `timeline.json`, `foreshadow.json`
- Agent project state: `story_bible.json`, `plot_threads.json`, `locations.json`, `organizations.json`, `style_guide.json`, `scenes.json`
- Review and recovery state: `suggestions/`, `reviews/`, `checkpoints/`, `snapshots/`

## Key Decisions

- File system + JSON + Markdown artifacts remain the persistence layer.
- No database, vector database, Web UI, or true multi-agent runtime is required for Phase 3 MVP.
- New agent project state may be read into context and diagnostics.
- Only registered formal state targets are committed by `commit_suggestion()`.
- LLM output must remain proposal data until review and commit make the transition explicit.

## Service Map

- Project Service: project metadata and canonical paths.
- Story Bible Service: enhanced state loading and legacy defaults.
- Context Assembly Service: targeted prompt context plus `context_audit`.
- Planner Service: current outline/volume/chapter planning, future arc/scene planning.
- Review Service: canonical review artifacts.
- Consistency Service: deterministic checks by default.
- Snapshot Service: formal state restore before/after commit failures.
- Status Service: workflow, artifact, snapshot, and formal-state diagnostics.
- Export Service: current chapter export and future whole-project export.

