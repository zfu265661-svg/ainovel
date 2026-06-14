from __future__ import annotations

from typing import Any

from domain.models.context import ContextPackage


class DeterministicLLMClient:
    """Replaceable local generator for tests and offline MVP runs."""

    def draft(self, chapter_plan: dict[str, Any], context: ContextPackage) -> str:
        title = chapter_plan.get("title") or f"Chapter {chapter_plan.get('chapter_id', '?')}"
        goal = chapter_plan.get("goal") or "Advance the story."
        mandatory = ", ".join(item["title"] for item in context.layers.get("mandatory", [])[:8])
        return (
            f"# {title}\n\n"
            f"Goal: {goal}\n\n"
            f"Mandatory continuity: {mandatory or 'none'}.\n\n"
            "The chapter draft moves the narrative forward while preserving the selected state."
        )

    def rewrite(self, draft: str, chapter_plan: dict[str, Any]) -> str:
        return draft + "\n\nRewrite pass: tightened continuity, clarified handoff, and preserved character state."

    def summarize(self, rewrite: str, chapter_plan: dict[str, Any]) -> str:
        title = chapter_plan.get("title") or f"Chapter {chapter_plan.get('chapter_id', '?')}"
        return f"{title}: {chapter_plan.get('goal') or 'The story advances.'}"

    def suggest_updates(self, chapter_plan: dict[str, Any], summary: str) -> dict[str, Any]:
        return {
            "chapter_summary": summary,
            "handoff": chapter_plan.get("handoff") or f"Continue from {chapter_plan.get('title') or 'this chapter'}.",
            "character_updates": [
                {"target": name, "content": f"Appeared in {chapter_plan.get('title') or 'chapter'}."}
                for name in chapter_plan.get("characters", [])
            ],
        }
