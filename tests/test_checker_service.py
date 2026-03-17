import json

import pytest

from core.checker_service import ConsistencyCheckParseError, check_consistency


def test_check_consistency_returns_parsed_dict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompt_template = '检查以下内容，并参考 JSON 示例：{"has_issue": false, "issues": [], "suggestions": []}'
    response_payload = {
        "has_issue": True,
        "issues": [{"type": "timeline", "description": "Timeline mismatch"}],
        "suggestions": ["Align chapter time with outline."],
    }

    monkeypatch.setattr("core.checker_service.load_prompt", lambda name: prompt_template)

    class FakeLLMClient:
        def generate_text(self, prompt: str) -> str:
            assert '{"has_issue": false, "issues": [], "suggestions": []}' in prompt
            assert "测试正文" in prompt
            assert '"title": "测试大纲"' in prompt
            return json.dumps(response_payload, ensure_ascii=False)

    monkeypatch.setattr("core.checker_service.LLMClient", FakeLLMClient)

    result = check_consistency(
        draft_text="测试正文",
        outline={"title": "测试大纲"},
        character_info={"hero": {"name": "林岚"}},
        timeline=[{"chapter": 1, "time": "Day 1"}],
    )

    assert result == response_payload


def test_check_consistency_raises_for_invalid_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("core.checker_service.load_prompt", lambda name: "prompt")

    class FakeLLMClient:
        def generate_text(self, prompt: str) -> str:
            return "not json"

    monkeypatch.setattr("core.checker_service.LLMClient", FakeLLMClient)

    with pytest.raises(ConsistencyCheckParseError, match="not valid JSON"):
        check_consistency("正文", {}, {}, [])


def test_check_consistency_raises_for_missing_required_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("core.checker_service.load_prompt", lambda name: "prompt")

    class FakeLLMClient:
        def generate_text(self, prompt: str) -> str:
            return json.dumps({"has_issue": False, "issues": []}, ensure_ascii=False)

    monkeypatch.setattr("core.checker_service.LLMClient", FakeLLMClient)

    with pytest.raises(
        ConsistencyCheckParseError,
        match="missing required field\\(s\\): suggestions",
    ):
        check_consistency("正文", {}, {}, [])


def test_check_consistency_raises_when_issues_is_not_a_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("core.checker_service.load_prompt", lambda name: "prompt")

    class FakeLLMClient:
        def generate_text(self, prompt: str) -> str:
            return json.dumps(
                {
                    "has_issue": True,
                    "issues": "not-a-list",
                    "suggestions": ["Fix issue format."],
                },
                ensure_ascii=False,
            )

    monkeypatch.setattr("core.checker_service.LLMClient", FakeLLMClient)

    with pytest.raises(ConsistencyCheckParseError, match="field 'issues' must be a list"):
        check_consistency("正文", {}, {}, [])
