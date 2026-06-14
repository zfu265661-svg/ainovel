# PlotPilot-Like MVP Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rebuild the project into a runnable long-form narrative engine MVP with domain state, chapter pipeline, trace/audit/report artifacts, FastAPI, Streamlit, CLI, docs, and tests.

**Architecture:** Add a clean layered architecture beside the existing legacy modules so the new product surface can run while legacy tests stay stable. The first persistence layer is JSON under `data/projects/{project_id}/`; LLM behavior is deterministic and replaceable to avoid API-key-dependent tests.

**Tech Stack:** Python dataclasses, JSON filesystem repository, FastAPI, Streamlit, pytest.

---

## Acceptance Criteria

- `python -m pytest` passes.
- CLI can initialize a demo project and run chapter 1.
- Chapter pipeline writes `trace.json`, `context_audit.json`, `consistency_report.json`, chapter markdown outputs, and checkpoint JSON.
- FastAPI exposes the requested read/run endpoints.
- Streamlit can inspect project state, chapters, ledgers, trace, audit, report, and checkpoints.

## Tasks

### Task 1: Domain Models

**Files:**
- Create: `domain/models/*.py`
- Create: `domain/__init__.py`, `domain/models/__init__.py`
- Test: `tests/test_new_domain_models.py`

Implement JSON-serializable dataclasses for projects, chapters, entities, narrative snapshot, context package, pipeline trace, consistency report, and checkpoint.

### Task 2: JSON Repository

**Files:**
- Create: `infrastructure/persistence/json_repository.py`
- Create: `infrastructure/config.py`
- Test: `tests/test_new_json_repository.py`

Implement canonical `data/projects/{project_id}/` layout and helpers for snapshot, chapter artifacts, traces, audits, reports, and checkpoints.

### Task 3: Context Assembler And Ledger Rules

**Files:**
- Create: `engine/context/context_layers.py`
- Create: `engine/context/context_audit.py`
- Create: `engine/context/context_assembler.py`
- Test: `tests/test_new_context_assembler.py`

Build mandatory/compressed/recent/optional context layers and required coverage audit.

### Task 4: Pipeline Trace, Consistency, Checkpoint

**Files:**
- Create: `engine/pipeline/stages.py`
- Create: `engine/pipeline/trace.py`
- Create: `engine/quality/consistency_checker.py`
- Create: `engine/runtime/checkpoint.py`
- Test: `tests/test_new_pipeline_quality_checkpoint.py`

Implement trace stages, deterministic consistency checks, and checkpoint persistence.

### Task 5: Chapter Pipeline And Use Cases

**Files:**
- Create: `engine/pipeline/chapter_pipeline.py`
- Create: `engine/runtime/engine_runner.py`
- Create: `infrastructure/llm/client.py`
- Create: `infrastructure/llm/prompts.py`
- Create: `application/use_cases/*.py`
- Test: `tests/test_new_run_chapter.py`

Implement the requested single-chapter pipeline with dry-run and review-before-commit support.

### Task 6: Interfaces

**Files:**
- Create: `interfaces/api/*.py`
- Create: `interfaces/cli/main.py`
- Create: `interfaces/streamlit/app.py`
- Test: `tests/test_new_api.py`

Expose minimal FastAPI routes and CLI commands. Streamlit is a simple operational dashboard.

### Task 7: Docs And Dependency Metadata

**Files:**
- Modify: `README.md`
- Modify: `requirements.txt`
- Create: `pyproject.toml`
- Create/replace: `docs/ARCHITECTURE.md`, `docs/API_DESIGN.md`, `docs/NARRATIVE_ENGINE.md`, `docs/DEVELOPMENT_ROADMAP.md`, `docs/MIGRATION_LOG.md`

Document install, CLI, API, Streamlit, storage layout, current MVP limits, and next steps.

### Task 8: Verification

Run:

```powershell
python -m pytest
```

Fix failures until the full test suite passes or clearly isolate external-only failures.
