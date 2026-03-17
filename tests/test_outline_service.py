import json

import pytest

from core.outline_service import OutlineParseError, generate_outline


def test_generate_outline_safely_injects_real_placeholders(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompt_template = "topic={topic};style={style};target={target}"
    outline = {
        "title": "测试标题",
        "core_hook": "核心卖点",
        "theme": "成长",
        "protagonist": {"name": "林岚"},
        "conflict": {"main_conflict": "生存危机"},
        "volume_plan": [{"volume_no": 1, "title": "第一卷"}],
    }

    monkeypatch.setattr("core.outline_service.load_prompt", lambda name: prompt_template)

    class FakeLLMClient:
        def generate_text(self, prompt: str) -> str:
            assert prompt == "topic=修仙;style=热血;target=长篇连载"
            return json.dumps(outline, ensure_ascii=False)

    monkeypatch.setattr("core.outline_service.LLMClient", FakeLLMClient)

    result = generate_outline("修仙", "热血", "长篇连载")

    assert result == outline


def test_generate_outline_does_not_fail_when_template_contains_json_braces(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompt_template = '请输出 JSON：{\n"title": "示例"\n}\n题材：{topic}\n风格：{style}\n目标：{target}'
    outline = {
        "title": "测试标题",
        "core_hook": "核心卖点",
        "theme": "成长",
        "protagonist": {"name": "林岚"},
        "conflict": {"main_conflict": "生存危机"},
        "volume_plan": [{"volume_no": 1, "title": "第一卷"}],
    }

    monkeypatch.setattr("core.outline_service.load_prompt", lambda name: prompt_template)

    class FakeLLMClient:
        def generate_text(self, prompt: str) -> str:
            assert '"title": "示例"' in prompt
            assert "题材：修仙" in prompt
            assert "风格：热血" in prompt
            assert "目标：长篇连载" in prompt
            return json.dumps(outline, ensure_ascii=False)

    monkeypatch.setattr("core.outline_service.LLMClient", FakeLLMClient)

    result = generate_outline("修仙", "热血", "长篇连载")

    assert result["title"] == "测试标题"


def test_generate_outline_raises_for_invalid_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("core.outline_service.load_prompt", lambda name: "{topic}")

    class FakeLLMClient:
        def generate_text(self, prompt: str) -> str:
            return "not json"

    monkeypatch.setattr("core.outline_service.LLMClient", FakeLLMClient)

    with pytest.raises(OutlineParseError, match="not valid JSON"):
        generate_outline("修仙", "热血", "长篇连载")


def test_generate_outline_raises_for_missing_required_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("core.outline_service.load_prompt", lambda name: "{topic}")

    class FakeLLMClient:
        def generate_text(self, prompt: str) -> str:
            return json.dumps(
                {
                    "title": "测试标题",
                    "core_hook": "核心卖点",
                    "theme": "成长",
                },
                ensure_ascii=False,
            )

    monkeypatch.setattr("core.outline_service.LLMClient", FakeLLMClient)

    with pytest.raises(
        OutlineParseError,
        match="missing required field\\(s\\): protagonist, conflict, volume_plan",
    ):
        generate_outline("修仙", "热血", "长篇连载")
