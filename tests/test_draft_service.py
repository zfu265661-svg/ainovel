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
            assert '"title": "第一章"' in prompt
            assert '"goal": "夜探"' in prompt
            assert '"name": "林砚"' in prompt
            assert "style=冷峻、克制" in prompt
            return "夜风卷过巷口，林砚按住刀鞘，缓步逼近院墙。"

    monkeypatch.setattr("core.draft_service.LLMClient", FakeLLMClient)

    result = generate_draft(
        chapter_plan={"title": "第一章", "goal": "夜探"},
        character_info={"name": "林砚"},
        style_rules="冷峻、克制",
    )

    assert result == "夜风卷过巷口，林砚按住刀鞘，缓步逼近院墙。"


def test_generate_draft_does_not_fail_when_template_contains_json_braces(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "core.draft_service.load_prompt",
        lambda name: '请参考 JSON：{"scene": "示例"}\n{chapter_plan}\n{character_info}\n{style_rules}',
    )

    class FakeLLMClient:
        def generate_text(self, prompt: str) -> str:
            assert '{"scene": "示例"}' in prompt
            assert '"title": "第一章"' in prompt
            assert '"name": "林砚"' in prompt
            return "正文内容"

    monkeypatch.setattr("core.draft_service.LLMClient", FakeLLMClient)

    result = generate_draft(
        chapter_plan={"title": "第一章"},
        character_info={"name": "林砚"},
        style_rules="冷峻",
    )

    assert result == "正文内容"


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
            chapter_plan={"title": "第一章"},
            character_info={"name": "林砚"},
            style_rules="冷峻、克制",
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
            chapter_plan={"title": "第一章"},
            character_info={"name": "林砚"},
            style_rules="冷峻、克制",
        )
