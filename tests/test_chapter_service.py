from __future__ import annotations

import json

import pytest

from core.chapter_service import (
    ChapterParseError,
    ChapterServiceError,
    generate_chapter_plan,
    generate_volume_chapters,
)


def test_generate_chapter_plan_safely_injects_real_placeholders(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompt_template = (
        "outline={outline};volume={volume_info};chapter={chapter_no};"
        "summary={previous_summary}"
    )
    chapter_plan = {
        "chapter_no": 3,
        "title": "Night Chase",
        "goal": "Find the source of the clue",
        "conflict": "The protagonist is one step behind the enemy.",
        "beats": [
            {"order": 1, "scene": "The protagonist heads out at night."},
            {"order": 2, "scene": "The key witness disappears."},
        ],
        "ending_hook": "A familiar mark appears on the wall.",
    }

    monkeypatch.setattr("core.chapter_service.load_prompt", lambda name: prompt_template)

    class FakeLLMClient:
        def generate_text_with_context(
            self,
            prompt: str,
            stage_name: str | None = None,
            volume_no: int | None = None,
        ) -> str:
            assert '"book_title": "Test Novel"' in prompt
            assert '"volume_no": 1' in prompt
            assert "chapter=3" in prompt
            assert "summary=previous summary" in prompt
            assert stage_name == "chapter planning"
            assert volume_no == 1
            return json.dumps(chapter_plan, ensure_ascii=False)

    monkeypatch.setattr("core.chapter_service.LLMClient", FakeLLMClient)

    result = generate_chapter_plan(
        {"book_title": "Test Novel"},
        {"volume_no": 1},
        3,
        "previous summary",
    )

    assert result == chapter_plan


def test_generate_chapter_plan_keeps_legacy_call_compatible(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "core.chapter_service.load_prompt",
        lambda name: "outline={outline};chapter={chapter_no};summary={previous_summary}",
    )

    class FakeLLMClient:
        def generate_text_with_context(
            self,
            prompt: str,
            stage_name: str | None = None,
            volume_no: int | None = None,
        ) -> str:
            assert "chapter=1" in prompt
            assert "summary=legacy summary" in prompt
            assert stage_name == "chapter planning"
            assert volume_no is None
            return json.dumps(
                {
                    "chapter_no": 1,
                    "title": "Opening",
                    "goal": "Introduce the threat",
                    "conflict": "The protagonist is dragged into trouble.",
                    "beats": [{"order": 1, "scene": "A letter arrives."}],
                    "ending_hook": "Someone knocks at the door.",
                },
                ensure_ascii=False,
            )

    monkeypatch.setattr("core.chapter_service.LLMClient", FakeLLMClient)

    result = generate_chapter_plan({"book_title": "Test Novel"}, 1, "legacy summary")

    assert result["chapter_no"] == 1


def test_generate_chapter_plan_raises_for_invalid_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("core.chapter_service.load_prompt", lambda name: "{chapter_no}")

    class FakeLLMClient:
        def generate_text_with_context(
            self,
            prompt: str,
            stage_name: str | None = None,
            volume_no: int | None = None,
        ) -> str:
            return "not json"

    monkeypatch.setattr("core.chapter_service.LLMClient", FakeLLMClient)

    with pytest.raises(ChapterParseError, match="not valid JSON"):
        generate_chapter_plan({"book_title": "Test Novel"}, 1, "legacy summary")


def test_generate_chapter_plan_raises_for_missing_required_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("core.chapter_service.load_prompt", lambda name: "{chapter_no}")

    class FakeLLMClient:
        def generate_text_with_context(
            self,
            prompt: str,
            stage_name: str | None = None,
            volume_no: int | None = None,
        ) -> str:
            return json.dumps(
                {
                    "chapter_no": 1,
                    "title": "Opening",
                    "goal": "Introduce the threat",
                },
                ensure_ascii=False,
            )

    monkeypatch.setattr("core.chapter_service.LLMClient", FakeLLMClient)

    with pytest.raises(
        ChapterParseError,
        match="missing required field\\(s\\): conflict, beats, ending_hook",
    ):
        generate_chapter_plan({"book_title": "Test Novel"}, 1, "legacy summary")


def test_generate_chapter_plan_raises_for_non_list_beats(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("core.chapter_service.load_prompt", lambda name: "{chapter_no}")

    class FakeLLMClient:
        def generate_text_with_context(
            self,
            prompt: str,
            stage_name: str | None = None,
            volume_no: int | None = None,
        ) -> str:
            return json.dumps(
                {
                    "chapter_no": 1,
                    "title": "Opening",
                    "goal": "Introduce the threat",
                    "conflict": "The protagonist is dragged into trouble.",
                    "beats": "not-a-list",
                    "ending_hook": "Someone knocks at the door.",
                },
                ensure_ascii=False,
            )

    monkeypatch.setattr("core.chapter_service.LLMClient", FakeLLMClient)

    with pytest.raises(ChapterParseError, match="field 'beats' must be a list"):
        generate_chapter_plan({"book_title": "Test Novel"}, 1, "legacy summary")


def test_generate_volume_chapters_returns_minimum_chapter_index(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("core.chapter_service.load_prompt", lambda name: "count={chapter_count};start={start_chapter_no};volume={volume_info}")

    class FakeLLMClient:
        call_count = 0

        def generate_text_with_context(
            self,
            prompt: str,
            stage_name: str | None = None,
            volume_no: int | None = None,
        ) -> str:
            FakeLLMClient.call_count += 1
            assert "count=2" in prompt
            assert "start=5" in prompt
            assert stage_name == "volume chapter planning"
            assert volume_no == 2
            return json.dumps(
                [
                    {
                        "chapter_no": 999,
                        "title": "Chapter 5",
                        "goal": "Goal 5",
                        "conflict": "Conflict",
                        "beats": [{"order": 1, "scene": "Opening"}],
                        "ending_hook": "Hook",
                    },
                    {
                        "chapter_no": 1000,
                        "title": "Chapter 6",
                        "goal": "Goal 6",
                        "conflict": "Conflict",
                        "beats": [{"order": 1, "scene": "Opening"}],
                        "ending_hook": "Hook",
                    },
                ],
                ensure_ascii=False,
            )

    monkeypatch.setattr("core.chapter_service.LLMClient", FakeLLMClient)

    result = generate_volume_chapters(
        outline={"book_title": "Test Novel"},
        volume_info={"volume_no": 2, "planned_chapters": 2},
        start_chapter_no=5,
    )

    assert result == [
        {
            "chapter_no": 5,
            "volume_no": 2,
            "title": "Chapter 5",
            "goal": "Goal 5",
            "conflict": "Conflict",
            "beats": [{"order": 1, "scene": "Opening"}],
            "ending_hook": "Hook",
            "status": "planned",
        },
        {
            "chapter_no": 6,
            "volume_no": 2,
            "title": "Chapter 6",
            "goal": "Goal 6",
            "conflict": "Conflict",
            "beats": [{"order": 1, "scene": "Opening"}],
            "ending_hook": "Hook",
            "status": "planned",
        },
    ]
    assert FakeLLMClient.call_count == 1


def test_generate_volume_chapters_raises_when_count_missing() -> None:
    with pytest.raises(
        ChapterServiceError,
        match="positive 'planned_chapters' or 'chapter_count'",
    ):
        generate_volume_chapters(
            outline={"book_title": "Test Novel"},
            volume_info={"volume_no": 1},
            start_chapter_no=1,
        )


def test_generate_volume_chapters_accepts_chapter_count_field(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("core.chapter_service.load_prompt", lambda name: "count={chapter_count};start={start_chapter_no};volume={volume_info}")

    class FakeLLMClient:
        call_count = 0

        def generate_text_with_context(
            self,
            prompt: str,
            stage_name: str | None = None,
            volume_no: int | None = None,
        ) -> str:
            FakeLLMClient.call_count += 1
            assert "count=2" in prompt
            assert "start=7" in prompt
            assert stage_name == "volume chapter planning"
            assert volume_no == 3
            return json.dumps(
                [
                    {
                        "chapter_no": 1,
                        "title": "Chapter 7",
                        "goal": "Goal 7",
                        "conflict": "Conflict",
                        "beats": [{"order": 1, "scene": "Opening"}],
                        "ending_hook": "Hook",
                    },
                    {
                        "chapter_no": 2,
                        "title": "Chapter 8",
                        "goal": "Goal 8",
                        "conflict": "Conflict",
                        "beats": [{"order": 1, "scene": "Opening"}],
                        "ending_hook": "Hook",
                    },
                ],
                ensure_ascii=False,
            )

    monkeypatch.setattr("core.chapter_service.LLMClient", FakeLLMClient)

    result = generate_volume_chapters(
        outline={"book_title": "Test Novel"},
        volume_info={"volume_no": 3, "chapter_count": 2},
        start_chapter_no=7,
    )

    assert result == [
        {
            "chapter_no": 7,
            "volume_no": 3,
            "title": "Chapter 7",
            "goal": "Goal 7",
            "conflict": "Conflict",
            "beats": [{"order": 1, "scene": "Opening"}],
            "ending_hook": "Hook",
            "status": "planned",
        },
        {
            "chapter_no": 8,
            "volume_no": 3,
            "title": "Chapter 8",
            "goal": "Goal 8",
            "conflict": "Conflict",
            "beats": [{"order": 1, "scene": "Opening"}],
            "ending_hook": "Hook",
            "status": "planned",
        },
    ]
    assert FakeLLMClient.call_count == 1


def test_generate_volume_chapters_parses_json_code_block_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("core.chapter_service.load_prompt", lambda name: "count={chapter_count}")

    class FakeLLMClient:
        def generate_text_with_context(
            self,
            prompt: str,
            stage_name: str | None = None,
            volume_no: int | None = None,
        ) -> str:
            return """```json
[
  {
    "chapter_no": 1,
    "title": "Chapter 1",
    "goal": "Goal 1",
    "conflict": "Conflict",
    "beats": [{"order": 1, "scene": "Opening"}],
    "ending_hook": "Hook"
  }
]
```"""

    monkeypatch.setattr("core.chapter_service.LLMClient", FakeLLMClient)

    result = generate_volume_chapters(
        outline={"book_title": "Test Novel"},
        volume_info={"volume_no": 1, "chapter_count": 1},
        start_chapter_no=1,
    )

    assert result[0]["chapter_no"] == 1
    assert result[0]["title"] == "Chapter 1"


def test_generate_volume_chapters_extracts_json_array_with_extra_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("core.chapter_service.load_prompt", lambda name: "count={chapter_count}")

    class FakeLLMClient:
        def generate_text_with_context(
            self,
            prompt: str,
            stage_name: str | None = None,
            volume_no: int | None = None,
        ) -> str:
            return """以下是结果：
[
  {
    "chapter_no": 1,
    "title": "Chapter 1",
    "goal": "Goal 1",
    "conflict": "Conflict",
    "beats": [{"order": 1, "scene": "Opening"}],
    "ending_hook": "Hook"
  }
]
请查收。"""

    monkeypatch.setattr("core.chapter_service.LLMClient", FakeLLMClient)

    result = generate_volume_chapters(
        outline={"book_title": "Test Novel"},
        volume_info={"volume_no": 1, "chapter_count": 1},
        start_chapter_no=1,
    )

    assert result[0]["chapter_no"] == 1
    assert result[0]["title"] == "Chapter 1"


def test_generate_volume_chapters_raises_clear_error_with_response_snippet_for_invalid_json(
    monkeypatch: pytest.MonkeyPatch,
    capsys,
) -> None:
    monkeypatch.setattr("core.chapter_service.load_prompt", lambda name: "count={chapter_count}")

    class FakeLLMClient:
        def generate_text_with_context(
            self,
            prompt: str,
            stage_name: str | None = None,
            volume_no: int | None = None,
        ) -> str:
            return """[
  {
    "chapter_no": 1,
    "title": "Broken"""

    monkeypatch.setattr("core.chapter_service.LLMClient", FakeLLMClient)

    with pytest.raises(
        ChapterParseError,
        match=r"Volume chapter plan response is not valid JSON: .*response_snippet=",
    ):
        generate_volume_chapters(
            outline={"book_title": "Test Novel"},
            volume_info={"volume_no": 1, "chapter_count": 1},
            start_chapter_no=1,
        )

    captured = capsys.readouterr()
    assert "stage=volume chapter planning status=parse_failure" in captured.err
