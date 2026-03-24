from __future__ import annotations

import pytest

from core.draft_service import DraftServiceError, generate_draft


def test_generate_draft_safely_injects_real_placeholders(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "core.draft_service.load_prompt",
        lambda name: "chapter={chapter_plan};characters={character_info};style={style_rules}",
    )

    class FakeLLMClient:
        def generate_text(self, prompt: str) -> str:
            assert '"title": "Chapter One"' in prompt
            assert '"goal": "Night exploration"' in prompt
            assert '"name": "Lin Yan"' in prompt
            assert "style=cold and restrained" in prompt
            return "A cold wind swept through the alley."

    monkeypatch.setattr("core.draft_service.LLMClient", FakeLLMClient)

    result = generate_draft(
        chapter_plan={"title": "Chapter One", "goal": "Night exploration"},
        character_info={"name": "Lin Yan"},
        style_rules="cold and restrained",
    )

    assert result == "A cold wind swept through the alley."


def test_generate_draft_does_not_fail_when_template_contains_json_braces(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "core.draft_service.load_prompt",
        lambda name: 'example={"scene": "sample"}\n{chapter_plan}\n{character_info}\n{style_rules}',
    )

    class FakeLLMClient:
        def generate_text(self, prompt: str) -> str:
            assert '{"scene": "sample"}' in prompt
            assert '"title": "Chapter One"' in prompt
            assert '"name": "Lin Yan"' in prompt
            return "Draft body"

    monkeypatch.setattr("core.draft_service.LLMClient", FakeLLMClient)

    result = generate_draft(
        chapter_plan={"title": "Chapter One"},
        character_info={"name": "Lin Yan"},
        style_rules="cold",
    )

    assert result == "Draft body"


def test_generate_draft_accepts_minimum_context_bundle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "core.draft_service.load_prompt",
        lambda name: (
            "chapter={chapter_plan};context={context_bundle};"
            "outline={outline};summary={previous_summary};"
            "timeline={timeline};foreshadow={foreshadow};style={style_rules}"
        ),
    )

    class FakeLLMClient:
        def generate_text(self, prompt: str) -> str:
            assert '"title": "Chapter One"' in prompt
            assert '"title": "Test Outline"' in prompt
            assert "Previous chapter summary" in prompt
            assert '"name": "Lin Yue"' in prompt
            assert '"event": "Earlier event"' in prompt
            assert '"content": "Old clue"' in prompt
            return "Draft body"

    monkeypatch.setattr("core.draft_service.LLMClient", FakeLLMClient)

    result = generate_draft(
        chapter_plan={"title": "Chapter One"},
        context_bundle={
            "outline": {"title": "Test Outline"},
            "previous_summary": "Previous chapter summary",
            "characters": [{"name": "Lin Yue"}],
            "timeline": [{"event": "Earlier event"}],
            "foreshadow": [{"content": "Old clue"}],
        },
        style_rules="cold",
    )

    assert result == "Draft body"


def test_generate_draft_raises_for_empty_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("core.draft_service.load_prompt", lambda name: "{chapter_plan}")

    class FakeLLMClient:
        def generate_text(self, prompt: str) -> str:
            return "   "

    monkeypatch.setattr("core.draft_service.LLMClient", FakeLLMClient)

    with pytest.raises(DraftServiceError, match="returned empty text"):
        generate_draft(
            chapter_plan={"title": "Chapter One"},
            character_info={"name": "Lin Yan"},
            style_rules="cold and restrained",
        )


def test_generate_draft_wraps_llm_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("core.draft_service.load_prompt", lambda name: "{chapter_plan}")

    class FakeLLMClient:
        def generate_text(self, prompt: str) -> str:
            raise RuntimeError("upstream timeout")

    monkeypatch.setattr("core.draft_service.LLMClient", FakeLLMClient)

    with pytest.raises(
        DraftServiceError,
        match="Failed to generate draft text: upstream timeout",
    ):
        generate_draft(
            chapter_plan={"title": "Chapter One"},
            character_info={"name": "Lin Yan"},
            style_rules="cold and restrained",
        )
