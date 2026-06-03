# PlotPilot Reference Plan

## Reference Scope

This project references PlotPilot for architecture ideas only:

- Narrative State Machine vocabulary.
- Story Bible as the top-level continuity surface.
- Plot thread graph concepts.
- Summary-chain based long-form memory.
- Autopilot, prompt strategy, and quality monitor boundaries.

No PlotPilot code is copied. The current repository remains a filesystem-backed
CLI novel agent kernel.

## Adopted in Phase 3.1

Phase 3.1 adds a read-only observability layer:

- `inspect-context` exposes one chapter's selected context and `context_audit`.
- `inspect-story-bible` reports Story Bible and enhanced state health.
- `inspect-plot-threads` reports story line status and future graph fields.
- `show-status` includes a compact `narrative_state_machine` overview.

These commands do not call LLM services and do not mutate state.

## Narrative State Machine

Current state is grouped as:

- Formal state: `characters.json`, `timeline.json`, `foreshadow.json`.
- Enhanced state: `story_bible.json`, `plot_threads.json`, `locations.json`,
  `organizations.json`, `style_guide.json`, `scenes.json`.
- Process artifacts: `suggestions/`, `reviews/`, `checkpoints/`, `snapshots/`,
  `loop_state.json`.
- Derived artifacts: chapter summaries, context audits, status reports, inspect
  reports, future quality reports, and future memory indexes.

Formal state remains the only commit target. Enhanced state is read into context
and diagnostics, but is not committed by `commit_suggestion()`.

## Story Bible Direction

Future Story Bible upgrades should be additive and legacy-compatible. Candidate
sections include:

- World setting, rules, themes, taboos, and narrative style.
- Character, location, organization, plot-thread, and foreshadow indexes.
- POV firewall and continuity constraints.
- Appearance frequency and scheduling hints.

Phase 3.1 does not migrate the schema.

## Plot Thread Graph Direction

`plot_threads.json` may evolve from a flat `threads` list into graph-aware story
threads. Future fields may include:

- Thread type: main, subplot, character, romance, conspiracy.
- Thread status: unresolved, active, resolved, dormant.
- Nodes with chapter refs, dependencies, unlocks, convergence, branch, and merge
  metadata.

Phase 3.1 only inspects fields when they already exist. It does not require graph
fields and does not render a visual graph.

## Summary And Retrieval Direction

The current default path should continue using chapter summaries and targeted
state selection instead of full-chapter prompt dumping.

Future memory retrieval can be introduced through a provider interface, but Phase
3.1 does not add `memory_index_service.py`, vector databases, or retrieval
dependencies. A future provider should be able to index rewrites, summaries,
events, and triples, then let the context assembler query it as an optional
source.

## Autopilot And Quality Direction

`run-five` remains the legacy regression path. Future `run`, `resume`, and
`recover` commands can share a stage-based state machine:

`load -> context -> draft -> rewrite -> summarize -> suggest -> review -> check -> snapshot -> commit -> checkpoint`

Future quality monitor work should start as deterministic reports: continuity,
foreshadow closure, character consistency, plot logic, style drift, tension, and
cliche scans. LLM deep checking should remain optional and outside the default
main flow.

## Not Adopted Now

Phase 3.1 does not adopt:

- Database persistence.
- Vector databases such as ChromaDB or FAISS.
- FastAPI, Vue, or Tauri.
- LangChain or LangGraph.
- A true multi-agent runtime.
- Prompt template rewrites.
- Automatic enhanced-state commits.
- Web UI or graph visualization.
