# Narrative Engine

The engine centers on `NarrativeSnapshot`, which contains:

- project id and current chapter
- Story Bible
- characters, locations, organizations
- plot threads and foreshadows
- scenes
- chapter summaries
- update timestamp

Chapter pipeline stages:

```text
prepare
load_snapshot
build_chapter_plan
assemble_context
draft
rewrite
summarize
suggest_updates
consistency_check
review_gate
commit_snapshot
save_outputs
checkpoint
finish
```

Each stage writes a `PipelineStageTrace` with status, timestamps, inputs, outputs, warnings, and errors.

Context assembly outputs:

- `mandatory`: plan entities, previous handoff, active plot threads, active foreshadows
- `compressed`: Story Bible and compact character state
- `recent`: recent summaries and scenes
- `optional`: dormant threads and dormant foreshadows

The deterministic consistency checker validates summary/handoff presence, context coverage, stale plot threads, overdue foreshadows, blank snapshot updates, conflicting character updates, trace stage presence, and output files.
