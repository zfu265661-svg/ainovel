from __future__ import annotations

import json
from typing import Any

from core.errors import DraftGenerationError
from core.llm_client import LLMClient
from core.prompt_loader import load_prompt


class DraftServiceError(DraftGenerationError):
    """Base exception for draft generation failures."""


def generate_draft(
    chapter_plan: dict[str, Any],
    character_info: dict[str, Any],
    style_rules: str,
) -> str:
    """Generate chapter draft text from the configured prompt template."""
    prompt_template = load_prompt("draft.txt")
    prompt = (
        prompt_template.replace(
            "{chapter_plan}",
            json.dumps(chapter_plan, ensure_ascii=False, indent=2),
        )
        .replace(
            "{character_info}",
            json.dumps(character_info, ensure_ascii=False, indent=2),
        )
        .replace("{style_rules}", style_rules)
    )

    try:
        draft_text = LLMClient().generate_text(prompt)
    except Exception as exc:
        raise DraftServiceError(f"Failed to generate draft text: {exc}") from exc

    if not draft_text.strip():
        raise DraftServiceError("Draft generation returned empty text.")

    return draft_text
