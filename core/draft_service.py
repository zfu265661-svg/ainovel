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
    context_bundle: dict[str, Any] | None = None,
    style_rules: str = "",
    character_info: dict[str, Any] | None = None,
) -> str:
    """Generate chapter draft text from the configured prompt template."""
    normalized_context_bundle = _normalize_context_bundle(
        context_bundle=context_bundle,
        character_info=character_info,
    )
    serialized_context_bundle = json.dumps(
        normalized_context_bundle,
        ensure_ascii=False,
        indent=2,
    )
    serialized_character_info = json.dumps(
        normalized_context_bundle.get("characters", {}),
        ensure_ascii=False,
        indent=2,
    )

    prompt_template = load_prompt("draft.txt")
    prompt = (
        prompt_template.replace(
            "{chapter_plan}",
            json.dumps(chapter_plan, ensure_ascii=False, indent=2),
        )
        .replace(
            "{character_info}",
            serialized_character_info,
        )
        .replace("{context_bundle}", serialized_context_bundle)
        .replace(
            "{outline}",
            json.dumps(normalized_context_bundle.get("outline", {}), ensure_ascii=False, indent=2),
        )
        .replace(
            "{previous_summary}",
            str(normalized_context_bundle.get("previous_summary", "")),
        )
        .replace(
            "{timeline}",
            json.dumps(normalized_context_bundle.get("timeline", []), ensure_ascii=False, indent=2),
        )
        .replace(
            "{foreshadow}",
            json.dumps(normalized_context_bundle.get("foreshadow", []), ensure_ascii=False, indent=2),
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


def _normalize_context_bundle(
    context_bundle: dict[str, Any] | None,
    character_info: dict[str, Any] | None,
) -> dict[str, Any]:
    if context_bundle is None:
        return {"characters": character_info or {}}

    normalized_context_bundle = dict(context_bundle)
    if character_info is not None and "characters" not in normalized_context_bundle:
        normalized_context_bundle["characters"] = character_info
    elif character_info is None and "characters" not in normalized_context_bundle:
        normalized_context_bundle["characters"] = context_bundle

    return normalized_context_bundle
