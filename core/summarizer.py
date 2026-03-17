from __future__ import annotations

from core.llm_client import LLMClient


SUMMARY_PROMPT_TEMPLATE = (
    "Summarize the previous chapter into a concise recap for generating the next "
    "chapter outline.\n"
    "Requirements:\n"
    "1. Keep the key events, character actions, conflict progression, and major "
    "outcomes.\n"
    "2. Return plain text only. Do not use JSON, headings, or bullet points.\n"
    "3. Keep the summary within {max_words} words.\n\n"
    "Previous chapter:\n{text}"
)


class SummarizerError(RuntimeError):
    """Base exception for previous-chapter summarization failures."""


def summarize_previous_chapter(text: str, max_words: int = 300) -> str:
    """Summarize the previous chapter into plain text for outline generation."""
    if not text.strip():
        raise SummarizerError("Previous chapter text cannot be empty.")

    prompt = SUMMARY_PROMPT_TEMPLATE.format(text=text, max_words=max_words)

    try:
        summary = LLMClient().generate_text(prompt)
    except Exception as exc:
        raise SummarizerError(f"Failed to summarize previous chapter: {exc}") from exc

    if not summary.strip():
        raise SummarizerError("Summarizer returned empty text.")

    return summary.strip()
