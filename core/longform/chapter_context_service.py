"""Placeholder for future longform chapter context assembly.

TODO:
- Reuse existing project state files once the resumable loop is wired in.
- Keep context assembly separate from loop_state.json, which only tracks progress.
- Do not connect this module into the main workflow in the current phase.
"""

from __future__ import annotations


def build_chapter_context(*args, **kwargs):
    raise NotImplementedError(
        "chapter_context_service is intentionally not implemented in this phase."
    )
