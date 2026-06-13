# Review Control

## Manual Review Path

Phase 3.2 adds a human-controlled review gate:

`prepare-review -> show-review/list-reviews -> approve-review or reject-review -> commit-approved`

`prepare-review` creates or refreshes a pending review from the canonical
suggestion and runs deterministic consistency checks. It does not write formal
story state.

`approve-review` and `reject-review` only update the review artifact. They do
not touch `characters.json`, `timeline.json`, or `foreshadow.json`.

`commit-approved` only commits a review whose normalized status is `approved`.
It uses `review.approved_suggestion`, then runs through the existing consistency,
snapshot, rollback, marker, and formal target protection.

## Status Compatibility

Review artifacts support these statuses:

- `pending`
- `approved`
- `rejected`
- `committed`

Old reviews without `status` are normalized at load time:

- `committed: true` means `committed`
- otherwise the review is treated as `pending`

There is no one-time migration. New fields are written lazily when reviews are
prepared, approved, rejected, or committed.

## State Transitions

Allowed:

- `pending -> approved`
- `pending -> rejected`
- `approved -> committed`

Not allowed:

- `approved -> rejected`
- `rejected -> approved`
- `committed -> anything`

Rejected reviews cannot be committed. Committed reviews cannot be approved,
rejected, or committed again.

## Legacy Path

`phase1_cli.py commit-suggestion` and `phase2_cli.py run-five` remain legacy
regression paths. They are not replaced by Phase 3.2. The new manual path is
available through `phase2_cli.py commit-approved`.

Formal commit targets remain limited to:

- `characters`
- `timeline`
- `foreshadow`

Enhanced state files such as Story Bible, plot threads, locations,
organizations, style guide, and scenes remain read-only for context, status, and
inspection diagnostics.
