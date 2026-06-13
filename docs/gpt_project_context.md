# GPT Project Context: AI Novel

This document is written for another GPT or coding agent that needs to quickly understand this repository before making suggestions or code changes.

## One-Sentence Summary

This repository is a project-driven long-form novel writing agent kernel. It is not a one-shot chapter generator. Its current focus is stabilizing a real 5-chapter workflow with explicit state transitions, auditable review/commit artifacts, lightweight consistency checks, and recoverability.

## Current Engineering Goal

The project is in Phase 2 stabilization after a real 5-chapter run.

Current priorities:

1. Keep multi-chapter continuity stable.
2. Make state transitions explicit and auditable.
3. Improve context assembly.
4. Improve suggestion -> review -> commit flow.
5. Add lightweight deterministic consistency checks.
6. Improve checkpoint / rollback / recoverability.
7. Improve status, reporting, and diagnostics.

Do not treat this as a greenfield rewrite. Prefer small, verifiable changes that preserve the existing 5-chapter path.

## Repository Layout

```text
D:/AI novel/
  app.py                         Compatibility CLI entry for the old basic workflow.
  phase1_cli.py                  Recommended Phase 1 CLI entry.
  phase2_cli.py                  Recommended Phase 2 longform CLI entry.
  config.py                      Environment and provider configuration.
  requirements.txt               Python dependencies.
  README.md                      Main user-facing overview.
  AGENTS.md                      Local coding and project instructions.

  core/
    workflow_service.py          Main Phase 1 workflow orchestration and commit logic.
    project_service.py           Project structure and canonical project paths.
    llm_client.py                OpenAI-compatible chat completion client.
    prompt_loader.py             Loads prompt templates from prompts/.
    storage.py                   UTF-8 JSON/text persistence helpers.
    outline_service.py           Outline generation and parsing.
    volume_service.py            Volume plan generation and parsing.
    chapter_service.py           Chapter plan generation and parsing.
    draft_service.py             Draft generation.
    rewrite_service.py           Rewrite stage.
    summarizer.py                Chapter summary generation.
    suggestion_service.py        Structured state suggestion generation.
    checker_service.py           LLM-based consistency checker, not in default Phase 2 path.
    character_service.py         Character state validation/load helpers.
    timeline_service.py          Timeline state validation/load helpers.
    foreshadow_service.py        Foreshadow state validation/load helpers.
    export_service.py            Simple chapter export helper.
    errors.py                    Shared error classes and JSON parsing helpers.

    longform/
      chapter_context_service.py     Context assembler for long-form chapters.
      loop_state_service.py          Loop state creation and transition helpers.
      project_state_repository.py    Longform paths, loop_state persistence, artifact paths.
      chapter_runner_service.py      Runs one chapter and writes checkpoint results.
      serial_workflow_service.py     Runs chapters sequentially through chapter 5.
      review_service.py             Creates/validates canonical review artifacts.
      consistency_service.py        Cheap deterministic review checks.
      snapshot_service.py           Pre-commit snapshot, restore, cleanup.
      status_service.py             Status and diagnostic aggregation.

  prompts/
    outline.txt
    volume_plan.txt
    volume_chapters.txt
    chapter_plan.txt
    draft.txt
    rewrite.txt
    summary.txt
    state_suggestion.txt
    consistency_check.txt

  docs/
    phase1.md
    phase2_longform_usage.md
    phase2_longform_design.md
    gpt_project_context.md       This file.

  tests/
    test_*.py                    Phase 1, services, storage, config, CLI, e2e tests.
    longform/test_*.py           Phase 2 longform state, review, snapshot, status tests.

  analysis/
    *.md                         Earlier reviews, test plans, release notes, gap reports.

  data/
    book.json                    Legacy/basic workflow output.

  workspace/
    ...                          Runtime project workspaces and generated novel projects.
```

## Recommended Entry Points

There are three root-level CLI files:

- `phase1_cli.py`: recommended Phase 1 entry.
- `phase2_cli.py`: recommended Phase 2 entry.
- `app.py`: compatibility entry for the older basic interactive workflow.

`app.py` is retained, but it is not the recommended main entry for the current long-form workflow.

## Runtime Configuration

Configuration is loaded in `config.py` through `python-dotenv`.

Required environment variables:

```env
OPENAI_API_KEY=...
MODEL_NAME=...
```

Optional environment variable:

```env
OPENAI_BASE_URL=https://api.openai.com/v1
```

The provider is OpenAI-compatible. `.env.example` includes a DeepSeek example:

```env
OPENAI_BASE_URL=https://api.deepseek.com
MODEL_NAME=deepseek-v4-flash
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Known dependency caveat: `core/llm_client.py` directly imports `httpx`, but `requirements.txt` currently does not explicitly list `httpx`. It may be present through the OpenAI SDK in the local environment, but a clean environment should declare direct imports explicitly.

## Phase 1: Single-Project / Single-Chapter Closure

Phase 1 pushes a novel project from an empty project root to a minimal auditable chapter workflow.

Commands:

```bash
python phase1_cli.py create-project --root "<project_root>" --title "<title>" --topic "<topic>" --style "<style>" --target "<target>"
python phase1_cli.py plan-novel --root "<project_root>"
python phase1_cli.py write-chapter --root "<project_root>" --chapter 1
python phase1_cli.py commit-suggestion --root "<project_root>" --chapter 1
```

Phase 1 command responsibilities:

- `create-project`: creates the initial project structure and canonical state files.
- `plan-novel`: generates outline, volume plan, and chapter plans.
- `write-chapter`: generates draft, rewrite, summary, and state suggestion for one chapter.
- `commit-suggestion`: commits a suggestion through review, consistency check, snapshot, and formal state update.

Typical Phase 1 project artifacts:

```text
<project_root>/
  project.json
  chapters.json
  characters.json
  timeline.json
  foreshadow.json
  docs/
    outline.md
    volumes.md
    ch001.plan.md
    ch001.draft.md
    ch001.rewrite.md
    ch001.summary.md
  suggestions/
    ch001.suggestion.json
  reviews/
    ch001.review.json
```

## Phase 2: Recoverable 5-Chapter Longform Loop

Phase 2 wraps the Phase 1 chapter workflow in a resumable sequential runner.

Commands:

```bash
python phase2_cli.py init-loop --root "<project_root>"
python phase2_cli.py show-status --root "<project_root>"
python phase2_cli.py run-five --root "<project_root>"
```

Phase 2 command responsibilities:

- `init-loop`: creates `loop_state.json`, `checkpoints/`, and `reviews/`.
- `show-status`: aggregates loop state, committed artifacts, checkpoint, review, suggestion, and snapshot diagnostics.
- `run-five`: runs from `loop_state.next_chapter_no` through chapter 5, stopping immediately on failure.

There is no separate `resume` command. Running `run-five` again resumes from the current recoverable position.

## Main Workflow

The intended long-form workflow is:

```text
plan -> draft -> rewrite -> summarize -> suggest -> review -> consistency_check -> commit
```

In code, the workflow is split this way:

- Planning and content generation: `core/workflow_service.py`, plus outline/chapter/draft/rewrite/summary/suggestion services.
- Context assembly: `core/longform/chapter_context_service.py`.
- Review and consistency checks: `core/longform/review_service.py` and `core/longform/consistency_service.py`.
- Formal state commit: `core/workflow_service.py`.
- Snapshot / restore: `core/longform/snapshot_service.py`.
- Phase 2 orchestration: `core/longform/chapter_runner_service.py` and `core/longform/serial_workflow_service.py`.
- Status diagnostics: `core/longform/status_service.py`.

Important implementation detail:

- `write_chapter()` handles context assembly, draft, rewrite, summary, and suggestion persistence.
- `commit_suggestion()` is the only public formal state commit entry.
- Both Phase 1 `commit-suggestion` and Phase 2 automatic progression call `commit_suggestion()`.

## Context Assembly Philosophy

The project should not maintain continuity by dumping full previous chapters into the model.

The intended default path uses:

- structured formal state,
- previous chapter summaries,
- targeted chapter context,
- timeline truncation,
- open foreshadow filtering.

`core/longform/chapter_context_service.py` is the explicit context assembler. It currently handles:

- chapter 1 previous summary as empty,
- missing previous summary as empty instead of fatal,
- compact character context,
- recent timeline selection,
- active/open foreshadow items.

## State Model and Artifacts

Formal story state lives in these canonical files:

```text
characters.json
timeline.json
foreshadow.json
```

Process state and audit artifacts are separate:

```text
loop_state.json
suggestions/chXXX.suggestion.json
reviews/chXXX.review.json
checkpoints/chXXX.checkpoint.json
snapshots/chXXX.snapshot.json
```

Artifact meanings:

- `loop_state.json`: process progress only; it does not carry formal story state.
- `suggestions/chXXX.suggestion.json`: raw AI proposal for state updates.
- `reviews/chXXX.review.json`: canonical commit basis, including `approved_suggestion`, `consistency_check`, and committed markers.
- `checkpoints/chXXX.checkpoint.json`: per-chapter attempt result, failure stage, error, artifacts, and loop state snapshot.
- `snapshots/chXXX.snapshot.json`: pre-commit formal state backup for restore. Successful commits normally delete the snapshot.

## Suggestion -> Review -> Commit

The project intentionally avoids silently overwriting formal state with raw AI suggestions.

Current commit path:

1. Load canonical suggestion.
2. Create or refresh canonical review.
3. Run deterministic consistency checks and write them to review.
4. Load review for commit.
5. Use `review.approved_suggestion` as the commit input.
6. Create a pending snapshot of formal state.
7. Write `characters.json`, `timeline.json`, and `foreshadow.json`.
8. Mark review and suggestion as committed.
9. Delete the snapshot after a fully successful commit.

If formal state write or marker write fails, snapshot restore is attempted.

## Consistency Checks

Default Phase 2 uses lightweight deterministic checks, not a heavy LLM consistency pipeline.

`core/longform/consistency_service.py` writes `consistency_check` into the review.

Current semantics:

- `blockers` stop formal commit.
- `warnings` are retained but do not stop commit.
- already committed reviews are not rechecked.
- `core/checker_service.py` contains LLM-based checking, but it is not part of the default long-form path.

## Recoverability

`core/longform/snapshot_service.py` manages recoverable commits.

Key ideas:

- Before formal state commit, a snapshot stores `state_before` for `characters.json`, `timeline.json`, and `foreshadow.json`.
- If formal state write or commit marker write fails, formal state is restored from snapshot.
- Before rerunning the same chapter, preflight snapshot handling resolves unresolved or stale snapshots.

Snapshot categories:

- unresolved snapshot: snapshot exists and review/suggestion are not both committed. Treat as unfinished commit and restore first.
- stale snapshot: snapshot exists but review/suggestion are already committed. Treat as cleanup residue, not a formal state rollback target.

## Status and Diagnostics

`phase2_cli.py show-status` calls `build_project_status_report()`.

Important reported fields include:

- `workflow_status`
- `current_chapter_no`
- `next_chapter_no`
- `loop_state_last_completed_chapter_no`
- `last_successfully_committed_chapter_no`
- `last_successfully_committed_source`
- `commit_scan_status`
- `commit_loop_drift`
- `last_attempted_chapter_no`
- `last_attempt_status`
- `last_failure_stage`
- `last_error`
- `unresolved_snapshot_exists`
- `stale_snapshot_exists`
- `artifact_focus_chapter_no`
- `artifact_relation_status`
- `checkpoint_path`
- `review_path`
- `suggestion_path`
- `snapshot_path`

Recommended troubleshooting order:

1. Check `checkpoint`.
2. Check `snapshot`.
3. Check `review`.
4. Check `suggestion`.

Reasoning:

- checkpoint is the summary index,
- snapshot explains recoverability state,
- review is the explicit commit basis,
- suggestion is only the raw AI proposal.

## Prompt Templates

Prompt templates live in `prompts/` and are loaded by `core/prompt_loader.py`.

Do not change prompt text unless the task explicitly asks for prompt changes. Prompt drift can change external behavior in hard-to-debug ways.

## Tests

The repository has broad pytest coverage:

- root `tests/test_*.py`: Phase 1, service-level, CLI, storage, config, and smoke tests.
- `tests/longform/test_*.py`: Phase 2 loop state, context, runner, review, consistency, snapshot, status tests.

Useful targeted test examples:

```bash
python -B -m pytest tests/test_config.py tests/test_llm_client.py
python -B -m pytest tests/test_phase1_cli.py tests/longform/test_phase2_cli.py
python -B -m pytest tests/test_workflow_commit_suggestion.py tests/longform/test_snapshot_service.py
python -B -m pytest tests/longform
```

For a workflow change, prefer targeted tests first, then broader longform tests.

## Known Boundaries and Non-Goals

Do not prioritize:

- 100+ chapter automation,
- broad greenfield rewrites,
- large UI work,
- heavy full-book LLM consistency pipelines in the default path,
- prompt rewrites unless explicitly requested,
- silent state semantic changes.

Current Phase 2 does not add a manual approve/reject UI. It creates canonical review artifacts automatically and still auto-commits through the existing command path.

## Recommended Reading Order for a New GPT

Read these first:

1. `AGENTS.md`
2. `README.md`
3. `docs/phase1.md`
4. `docs/phase2_longform_usage.md`
5. `docs/phase2_longform_design.md`
6. `phase1_cli.py`
7. `phase2_cli.py`
8. `core/workflow_service.py`
9. `core/longform/chapter_context_service.py`
10. `core/longform/review_service.py`
11. `core/longform/consistency_service.py`
12. `core/longform/snapshot_service.py`
13. `core/longform/status_service.py`

## How to Reason About Changes

Before changing code, determine which layer is affected:

- content generation,
- structured state management,
- orchestration,
- persistence,
- review/checking,
- recovery,
- diagnostics.

Then make the smallest change that preserves the existing external behavior unless the task explicitly asks to change it.

When changing state semantics, document the transition and add or update tests.

When touching the workflow path, protect the 5-chapter path first.
