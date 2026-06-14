from __future__ import annotations


PIPELINE_STAGES = (
    "prepare",
    "load_snapshot",
    "build_chapter_plan",
    "assemble_context",
    "draft",
    "rewrite",
    "summarize",
    "suggest_updates",
    "consistency_check",
    "review_gate",
    "commit_snapshot",
    "save_outputs",
    "checkpoint",
    "finish",
)
