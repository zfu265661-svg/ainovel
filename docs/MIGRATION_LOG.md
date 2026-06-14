# Migration Log

## 2026-06-14

Added a new PlotPilot-inspired MVP architecture while keeping legacy modules in place for compatibility with existing tests. New runtime data is canonicalized under `data/projects/{project_id}/`.

No PlotPilot source code was copied. The implementation borrows architectural ideas: narrative snapshot, layered context, traceable chapter pipeline, deterministic quality gates, checkpoint artifacts, and thin interface adapters.
