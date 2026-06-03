# Agent Design

## Phase 3 MVP

Phase 3 does not start real parallel agents. It maps agent responsibilities to service boundaries so future work can replace or split services without changing the stable workflow contract.

## Role Mapping

- Story Architect: owns Story Bible structure, themes, world rules, and long-range structure.
- Plot Planner: owns outline, volume plan, chapter plan, future arc/scene plans.
- Character Keeper: owns character continuity and growth arcs.
- World Keeper: owns world, locations, organizations, and rules.
- Draft Writer: owns draft generation from chapter plan and assembled context.
- Rewriter: owns rewrite/polish stage.
- Continuity Checker: owns deterministic continuity checks by default.
- Style Editor: future optional style checks and edit stage.
- Review Manager: owns suggestion -> review -> consistency_check -> commit.
- Exporter: owns export artifacts.

## Current Implementation Boundary

Current formal commits are restricted to:

- `characters.json`
- `timeline.json`
- `foreshadow.json`

The registry is implemented in `core/longform/state_targets.py`. Future targets can be added only after tests define validation, snapshot, restore, and commit semantics.

## Not In Scope Yet

- true multi-agent orchestration
- automatic human approval UI
- scene-first default writing
- vector retrieval
- LLM-based full-book consistency checks in the default path

