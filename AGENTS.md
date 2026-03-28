# AGENTS.md

## Repository goal
This repository is a project-driven long-form novel writing agent kernel.
It is not a one-shot chapter generator.

The current objective is Phase 2 stabilization after a real 5-chapter run:
- keep multi-chapter continuity stable
- make state transitions explicit and auditable
- improve context assembly, review/commit flow, lightweight consistency checks, and recoverability

## Current project shape
Important paths:
- `app.py`: current CLI entry
- `core/`: business logic and workflows
- `prompts/`: prompt templates
- `tests/`: automated tests
- `data/`: runtime outputs and generated artifacts

Treat this repository as an existing working codebase under controlled evolution, not a greenfield rewrite.

## Working style
Always prefer:
1. small, verifiable changes
2. plan first for multi-file or architecture work
3. preserving current external behavior unless the task explicitly changes it
4. tests added or updated in the same change when practical
5. minimal-diff refactors over large rewrites

Do not:
- rewrite the repository from scratch
- rename many files unless clearly justified
- introduce new dependencies unless necessary and explained
- change prompt text in `prompts/` unless the task explicitly asks for it
- silently alter state semantics without documenting the transition

## Current engineering priority
Priority order for the next phase:
1. `context assembler`
2. `suggestion -> review -> commit`
3. lightweight `consistency checks`
4. `checkpoint / rollback`
5. clearer `status / reporting / diagnostics`

Do not prioritize:
- 100+ chapter automation
- heavy full-book LLM consistency pipelines in the default path
- large UI work
- broad cosmetic refactors

## Architecture intent
The intended long-form workflow is:

`plan -> draft -> rewrite -> summarize -> suggest -> review -> commit`

Key principle:
- chapter continuity should rely on structured state + summaries + targeted context,
  not on dumping full previous chapters into the model.

State changes must be auditable.
AI may propose updates, but core state should not be silently overwritten without an explicit review/commit step.

## File and module guidance
When touching code, preserve the distinction between:
- content generation
- structured state management
- orchestration
- persistence
- review/checking

Prefer to keep or evolve this boundary:
- planning / outline / chapter planning
- draft generation
- rewrite
- summary generation
- suggestion generation
- state commit
- checking / validation
- persistence / repository
- workflow orchestration

If a module is too large, prefer extracting a narrow helper or stage-specific function
instead of doing a broad rewrite.

## Planning rule
For any major feature, multi-file refactor, or workflow change:
- create or update a plan before implementation
- if `PLANS.md` exists, follow it
- if no plan exists, propose one first

A good plan must include:
- goal
- affected files
- tests
- risks
- acceptance criteria

## Test and verification expectations
Before claiming completion:
1. run the smallest relevant test set
2. if the change affects shared workflow behavior, run broader workflow tests
3. summarize:
   - what changed
   - what was tested
   - remaining risks
   - whether external behavior changed

Prefer targeted tests first, then broader validation.

## Review expectations
When reviewing or self-checking changes, focus on:
- correctness
- regressions
- state transition bugs
- continuity bugs across chapters
- missing or weak tests
- failure path handling
- accidental prompt / persistence / schema drift

De-prioritize purely cosmetic comments unless they reduce real maintenance risk.

## Done means
A task is done only if:
- the requested scope is implemented
- relevant tests pass or a clear reason is given why they cannot run
- the change preserves or intentionally updates external behavior
- risks are documented
- no unrelated refactor was bundled in

## Preferred implementation strategy
For this repository, default to this order:
1. inspect current behavior
2. write or update a plan
3. add or tighten tests
4. implement the smallest safe change
5. run verification
6. review diff and summarize risk

## Special guidance for this project
This repository is evolving from a working prototype into a stable novel-project kernel.

That means:
- protect the existing 5-chapter path
- prefer controlled migration over replacement
- make state, summary, and context flows explicit
- improve recoverability before expanding automation
- keep long-form continuity as the main evaluation standard

## If unsure
If requirements are ambiguous:
- first ask whether the change belongs to the default workflow or a companion/optional workflow
- prefer the safer, narrower interpretation
- do not assume a broad architecture rewrite is desired