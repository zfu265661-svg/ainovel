# Recoverability

## Recovery Model

The repository treats generated content and formal state differently:

- Drafts, rewrites, summaries, suggestions, reviews, and checkpoints are auditable artifacts.
- `characters.json`, `timeline.json`, and `foreshadow.json` are registered formal state.
- Formal state is written only after review and deterministic checks.

## Snapshot Semantics

Before commit writes formal state, `commit_suggestion()` creates:

`snapshots/chXXX.snapshot.json`

The snapshot stores full pre-commit payloads for each registered formal state target.

If a formal write or marker write fails, restore logic attempts to:

- reset review/suggestion committed markers
- restore formal state payloads
- mark the snapshot as restored with the failure reason

Successful commits delete the pending snapshot.

## Preflight Semantics

Before a new commit attempt, unresolved snapshots are handled first:

- if review and suggestion are already committed, the snapshot is stale and is cleaned
- otherwise the snapshot is treated as unfinished commit state and restored

Cleanup failures are explicit errors.

## Status Diagnostics

`show-status` reports:

- snapshot health
- checkpoint/review/suggestion/snapshot paths
- artifact relation status
- formal state health
- missing required or optional files
- corrupt files
- `can_continue`
- `next_action`

