# Workflow

## Current Default Path

The current single-chapter path is:

`plan -> draft -> rewrite -> summarize -> suggest -> review -> consistency_check -> commit`

`write_chapter()` handles content generation and proposal creation. `commit_suggestion()` is the only public formal-state commit entry.

## Phase 2 Loop

`phase2_cli.py run-five` keeps the 5-chapter regression path:

- resume from `loop_state.next_chapter_no`
- run one chapter at a time
- stop immediately on failure
- write checkpoint diagnostics
- advance loop state only after commit succeeds

## Phase 3 Context Flow

Before drafting, `write_chapter()` loads:

- outline and chapter plan
- previous chapter summary
- characters, timeline, foreshadow
- Story Bible, plot threads, locations, organizations, style guide, scenes

`build_chapter_context()` compacts and selects relevant context, then returns `context_audit` so selection is explicit and testable.

## Review And Commit Flow

The legacy commit path still follows:

1. load canonical suggestion
2. create or refresh review
3. run deterministic consistency checks
4. load review as commit input
5. create pending snapshot
6. write registered formal state targets
7. mark review and suggestion committed
8. clean snapshot

Current registered targets are characters, timeline, and foreshadow.

## Manual Review Control

Phase 3.2 adds a manual path:

`prepare-review -> approve-review/reject-review -> commit-approved`

`commit-approved` requires an approved review and uses
`review.approved_suggestion` as the only formal commit input. Pending, rejected,
missing, and already committed reviews are rejected before formal state is
written.

`run-five` and `commit_suggestion()` remain legacy regression paths.

## Future Extensions

Future scene, style, plot, and Story Bible commits should reuse the same review/commit/snapshot pattern rather than introducing direct state writes.
