import json

import pytest

from core.chapter_service import ChapterParseError, generate_chapter_plan


def test_generate_chapter_plan_safely_injects_real_placeholders(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompt_template = "outline={outline};chapter={chapter_no};summary={previous_summary}"
    chapter_plan = {
        "chapter_no": 3,
        "title": "夜雨追踪",
        "goal": "找到线索来源",
        "conflict": "主角被人抢先一步",
        "beats": [
            {"order": 1, "scene": "主角深夜赴约"},
            {"order": 2, "scene": "线人突然失踪"},
        ],
        "ending_hook": "主角在墙上看到熟悉的记号",
    }

    monkeypatch.setattr("core.chapter_service.load_prompt", lambda name: prompt_template)

    class FakeLLMClient:
        def generate_text(self, prompt: str) -> str:
            assert '"book_title": "测试小说"' in prompt
            assert "chapter=3" in prompt
            assert "summary=上一章主角收到匿名线索" in prompt
            return json.dumps(chapter_plan, ensure_ascii=False)

    monkeypatch.setattr("core.chapter_service.LLMClient", FakeLLMClient)

    result = generate_chapter_plan(
        {"book_title": "测试小说"},
        3,
        "上一章主角收到匿名线索",
    )

    assert result == chapter_plan


def test_generate_chapter_plan_does_not_fail_when_template_contains_json_braces(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompt_template = (
        '请输出 JSON：{\n"chapter_no": 1,\n"title": "示例"\n}\n'
        "大纲：{outline}\n章节：{chapter_no}\n摘要：{previous_summary}"
    )
    chapter_plan = {
        "chapter_no": 1,
        "title": "开章",
        "goal": "引出危机",
        "conflict": "主角被迫卷入事件",
        "beats": [{"order": 1, "scene": "主角接到来信"}],
        "ending_hook": "门外传来敲门声",
    }

    monkeypatch.setattr("core.chapter_service.load_prompt", lambda name: prompt_template)

    class FakeLLMClient:
        def generate_text(self, prompt: str) -> str:
            assert '"chapter_no": 1' in prompt
            assert '"title": "示例"' in prompt
            assert '"book_title": "测试小说"' in prompt
            assert "章节：1" in prompt
            assert "摘要：无" in prompt
            return json.dumps(chapter_plan, ensure_ascii=False)

    monkeypatch.setattr("core.chapter_service.LLMClient", FakeLLMClient)

    result = generate_chapter_plan({"book_title": "测试小说"}, 1, "无")

    assert result["chapter_no"] == 1


def test_generate_chapter_plan_raises_for_invalid_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("core.chapter_service.load_prompt", lambda name: "{chapter_no}")

    class FakeLLMClient:
        def generate_text(self, prompt: str) -> str:
            return "not json"

    monkeypatch.setattr("core.chapter_service.LLMClient", FakeLLMClient)

    with pytest.raises(ChapterParseError, match="not valid JSON"):
        generate_chapter_plan({"book_title": "测试小说"}, 1, "无")


def test_generate_chapter_plan_raises_for_missing_required_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("core.chapter_service.load_prompt", lambda name: "{chapter_no}")

    class FakeLLMClient:
        def generate_text(self, prompt: str) -> str:
            return json.dumps(
                {
                    "chapter_no": 1,
                    "title": "开章",
                    "goal": "引出危机",
                },
                ensure_ascii=False,
            )

    monkeypatch.setattr("core.chapter_service.LLMClient", FakeLLMClient)

    with pytest.raises(
        ChapterParseError,
        match="missing required field\\(s\\): conflict, beats, ending_hook",
    ):
        generate_chapter_plan({"book_title": "测试小说"}, 1, "无")


def test_generate_chapter_plan_raises_for_non_list_beats(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("core.chapter_service.load_prompt", lambda name: "{chapter_no}")

    class FakeLLMClient:
        def generate_text(self, prompt: str) -> str:
            return json.dumps(
                {
                    "chapter_no": 1,
                    "title": "开章",
                    "goal": "引出危机",
                    "conflict": "主角被迫卷入事件",
                    "beats": "不是列表",
                    "ending_hook": "门外传来敲门声",
                },
                ensure_ascii=False,
            )

    monkeypatch.setattr("core.chapter_service.LLMClient", FakeLLMClient)

    with pytest.raises(ChapterParseError, match="field 'beats' must be a list"):
        generate_chapter_plan({"book_title": "测试小说"}, 1, "无")
