from __future__ import annotations

import json

import pytest

from core.volume_service import VolumeParseError, generate_volume_plan


def test_generate_volume_plan_returns_valid_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompt_template = "outline={outline}"
    outline = {
        "title": "测试小说",
        "core_hook": "核心卖点",
    }
    volume_plan = [
        {
            "volume_no": 1,
            "title": "第一卷",
            "goal": "建立主线",
            "core_conflict": "主角与宗门冲突",
        },
        {
            "volume_no": 2,
            "title": "第二卷",
            "goal": "扩展世界",
            "core_conflict": "外部势力入场",
        },
    ]

    monkeypatch.setattr("core.volume_service.load_prompt", lambda name: prompt_template)

    class FakeLLMClient:
        def generate_text(self, prompt: str) -> str:
            assert '"title": "测试小说"' in prompt
            return json.dumps(volume_plan, ensure_ascii=False)

    monkeypatch.setattr("core.volume_service.LLMClient", FakeLLMClient)

    result = generate_volume_plan(outline)

    assert isinstance(result, list)
    assert result == volume_plan


def test_generate_volume_plan_raises_for_empty_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("core.volume_service.load_prompt", lambda name: "{outline}")

    class FakeLLMClient:
        def generate_text(self, prompt: str) -> str:
            return "   "

    monkeypatch.setattr("core.volume_service.LLMClient", FakeLLMClient)

    with pytest.raises(VolumeParseError, match="Volume plan response is empty"):
        generate_volume_plan({"title": "测试小说"})


def test_generate_volume_plan_raises_for_invalid_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("core.volume_service.load_prompt", lambda name: "{outline}")

    class FakeLLMClient:
        def generate_text(self, prompt: str) -> str:
            return "not json"

    monkeypatch.setattr("core.volume_service.LLMClient", FakeLLMClient)

    with pytest.raises(VolumeParseError, match="not valid JSON"):
        generate_volume_plan({"title": "测试小说"})


def test_generate_volume_plan_raises_for_invalid_structure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("core.volume_service.load_prompt", lambda name: "{outline}")

    class FakeLLMClient:
        def generate_text(self, prompt: str) -> str:
            return json.dumps(
                [
                    {
                        "volume_no": 1,
                        "title": "第一卷",
                        "goal": "建立主线",
                    }
                ],
                ensure_ascii=False,
            )

    monkeypatch.setattr("core.volume_service.LLMClient", FakeLLMClient)

    with pytest.raises(
        VolumeParseError,
        match="missing required field\\(s\\): core_conflict",
    ):
        generate_volume_plan({"title": "测试小说"})
