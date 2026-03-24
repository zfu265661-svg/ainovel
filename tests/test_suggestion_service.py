from __future__ import annotations

import json

import pytest

from core.suggestion_service import SuggestionParseError, generate_state_suggestions


def test_generate_state_suggestions_returns_parsed_dict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompt_template = (
        "chapter={chapter_no}\n"
        "outline={outline}\n"
        "plan={chapter_plan}\n"
        "rewrite={rewritten_text}\n"
        "summary={chapter_summary}\n"
        "characters={characters}\n"
        "timeline={timeline}\n"
        "foreshadow={foreshadow}"
    )
    response_payload = {
        "chapter_no": 3,
        "character_updates": [
            {
                "action": "update",
                "target": "Lin Yue",
                "content": "对师门的信任下降。",
            }
        ],
        "timeline_updates": [
            {
                "action": "add",
                "target": "chapter_3",
                "content": "林月在古庙中发现暗门。",
            }
        ],
        "foreshadow_updates": [
            {
                "action": "add",
                "target": "jade_pendant",
                "content": "玉佩对古庙石门产生反应。",
            }
        ],
        "notes": "这些内容仅为建议，需后续人工确认。",
    }

    monkeypatch.setattr("core.suggestion_service.load_prompt", lambda name: prompt_template)

    class FakeLLMClient:
        def generate_text(self, prompt: str) -> str:
            assert "chapter=3" in prompt
            assert '"title": "测试总纲"' in prompt
            assert "改写后的正文" in prompt
            assert "章节摘要文本" in prompt
            return json.dumps(response_payload, ensure_ascii=False)

    monkeypatch.setattr("core.suggestion_service.LLMClient", FakeLLMClient)

    result = generate_state_suggestions(
        chapter_no=3,
        outline={"title": "测试总纲"},
        chapter_plan={"chapter_no": 3, "title": "第三章"},
        rewritten_text="改写后的正文",
        chapter_summary="章节摘要文本",
        characters=[{"name": "Lin Yue"}],
        timeline=[{"chapter_no": 2, "event": "上一章事件"}],
        foreshadow=[{"id": "fs-1", "content": "旧伏笔"}],
    )

    assert result == response_payload


def test_generate_state_suggestions_raises_for_empty_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("core.suggestion_service.load_prompt", lambda name: "prompt")

    class FakeLLMClient:
        def generate_text(self, prompt: str) -> str:
            return "   "

    monkeypatch.setattr("core.suggestion_service.LLMClient", FakeLLMClient)

    with pytest.raises(SuggestionParseError, match="State suggestion response is empty"):
        generate_state_suggestions(1, {}, {}, "正文", "摘要", [], [], [])


def test_generate_state_suggestions_raises_for_invalid_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("core.suggestion_service.load_prompt", lambda name: "prompt")

    class FakeLLMClient:
        def generate_text(self, prompt: str) -> str:
            return "not json"

    monkeypatch.setattr("core.suggestion_service.LLMClient", FakeLLMClient)

    with pytest.raises(SuggestionParseError, match="not valid JSON"):
        generate_state_suggestions(1, {}, {}, "正文", "摘要", [], [], [])


def test_generate_state_suggestions_raises_for_missing_required_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("core.suggestion_service.load_prompt", lambda name: "prompt")

    class FakeLLMClient:
        def generate_text(self, prompt: str) -> str:
            return json.dumps(
                {
                    "chapter_no": 1,
                    "character_updates": [],
                    "timeline_updates": [],
                    "notes": "缺少伏笔字段",
                },
                ensure_ascii=False,
            )

    monkeypatch.setattr("core.suggestion_service.LLMClient", FakeLLMClient)

    with pytest.raises(
        SuggestionParseError,
        match="missing required field\\(s\\): foreshadow_updates",
    ):
        generate_state_suggestions(1, {}, {}, "正文", "摘要", [], [], [])
