from __future__ import annotations

import pytest

from core.summarizer import SummarizerError, summarize_previous_chapter


def test_summarize_previous_chapter_returns_summary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "core.summarizer.load_prompt",
        lambda name: "Limit {max_words} words.\nPrevious chapter:\n{text}",
    )

    class FakeLLMClient:
        def generate_text(self, prompt: str) -> str:
            assert "Limit 120 words." in prompt
            assert "Previous chapter:" in prompt
            assert "Lin Yue slipped into the ruined temple." in prompt
            return "Lin Yue entered the ruined temple, found a clue, and confirmed the enemy was already watching."

    monkeypatch.setattr("core.summarizer.LLMClient", FakeLLMClient)

    result = summarize_previous_chapter(
        "Lin Yue slipped into the ruined temple.", max_words=120
    )

    assert (
        result
        == "Lin Yue entered the ruined temple, found a clue, and confirmed the enemy was already watching."
    )


def test_summarize_previous_chapter_raises_for_empty_input() -> None:
    with pytest.raises(SummarizerError, match="cannot be empty"):
        summarize_previous_chapter("   ")


def test_summarize_previous_chapter_raises_for_empty_model_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "core.summarizer.load_prompt",
        lambda name: "Summary prompt {max_words}\n{text}",
    )

    class FakeLLMClient:
        def generate_text(self, prompt: str) -> str:
            return "   "

    monkeypatch.setattr("core.summarizer.LLMClient", FakeLLMClient)

    with pytest.raises(SummarizerError, match="returned empty text"):
        summarize_previous_chapter("Previous chapter content.")


def test_summarize_previous_chapter_wraps_llm_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "core.summarizer.load_prompt",
        lambda name: "Summary prompt {max_words}\n{text}",
    )

    class FakeLLMClient:
        def generate_text(self, prompt: str) -> str:
            raise RuntimeError("upstream timeout")

    monkeypatch.setattr("core.summarizer.LLMClient", FakeLLMClient)

    with pytest.raises(
        SummarizerError,
        match="Failed to summarize previous chapter: upstream timeout",
    ):
        summarize_previous_chapter("Previous chapter content.")
