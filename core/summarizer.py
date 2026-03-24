from __future__ import annotations

from core.llm_client import LLMClient
from core.prompt_loader import load_prompt


class SummarizerError(RuntimeError):
    """Base exception for previous-chapter summarization failures."""


def summarize_previous_chapter(text: str, max_words: int = 300) -> str:
    """Summarize the previous chapter into plain text for outline generation."""
    if not text.strip():
        raise SummarizerError("Previous chapter text cannot be empty.")

    prompt_template = load_prompt("summary.txt")
    prompt = (
        prompt_template.replace("{max_words}", str(max_words))
        .replace("{text}", text)
    )

    try:
        summary = LLMClient().generate_text(prompt)
    except Exception as exc:
        raise SummarizerError(f"Failed to summarize previous chapter: {exc}") from exc

    if not summary.strip():
        raise SummarizerError("Summarizer returned empty text.")

    return summary.strip()
