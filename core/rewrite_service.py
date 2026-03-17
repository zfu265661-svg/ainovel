from __future__ import annotations

from core.errors import RewriteError
from core.llm_client import LLMClient
from core.prompt_loader import load_prompt


class RewriteServiceError(RewriteError, ValueError):
    """Raised when rewrite input or model output is invalid."""


def rewrite_text(text: str) -> str:
    """Rewrite novel body text with the configured rewrite prompt."""
    if not text or not text.strip():
        raise RewriteServiceError("Rewrite text cannot be empty or whitespace only.")

    prompt_template = load_prompt("rewrite.txt")
    prompt = prompt_template.replace("{text}", text)

    try:
        rewritten_text = LLMClient().generate_text(prompt)
    except Exception as exc:
        raise RewriteServiceError(f"Rewrite generation failed: {exc}") from exc

    if not rewritten_text or not rewritten_text.strip():
        raise RewriteServiceError("Rewrite model returned empty text.")

    return rewritten_text
