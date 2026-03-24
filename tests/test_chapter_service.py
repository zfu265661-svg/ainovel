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
        def generate_text(self, prompt: str) -> str:
            assert '"book_title": "Test Novel"' in prompt
            assert '"volume_no": 1' in prompt
            assert "chapter=3" in prompt
            assert "summary=previous summary" in prompt
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
        def generate_text(self, prompt: str) -> str:
            assert "chapter=1" in prompt
            assert "summary=legacy summary" in prompt
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
        def generate_text(self, prompt: str) -> str:
            return "not json"

    monkeypatch.setattr("core.chapter_service.LLMClient", FakeLLMClient)

    with pytest.raises(ChapterParseError, match="not valid JSON"):
        generate_chapter_plan({"book_title": "Test Novel"}, 1, "legacy summary")


def test_generate_chapter_plan_raises_for_missing_required_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("core.chapter_service.load_prompt", lambda name: "{chapter_no}")

    class FakeLLMClient:
        def generate_text(self, prompt: str) -> str:
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
        def generate_text(self, prompt: str) -> str:
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
    generated_calls: list[tuple[dict[str, object], dict[str, object], int, str]] = []

    def fake_generate_chapter_plan(
        outline: dict[str, object],
        volume_info: dict[str, object] | int | None = None,
        chapter_no: int | str = 1,
        previous_summary: str = "",
    ) -> dict[str, object]:
        assert isinstance(volume_info, dict)
        assert isinstance(chapter_no, int)
        generated_calls.append((outline, volume_info, chapter_no, previous_summary))
        return {
            "chapter_no": chapter_no,
            "title": f"Chapter {chapter_no}",
            "goal": f"Goal {chapter_no}",
            "conflict": "Conflict",
            "beats": [{"order": 1, "scene": "Opening"}],
            "ending_hook": "Hook",
        }

    monkeypatch.setattr("core.chapter_service.generate_chapter_plan", fake_generate_chapter_plan)

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
    assert generated_calls == [
        ({"book_title": "Test Novel"}, {"volume_no": 2, "planned_chapters": 2}, 5, ""),
        ({"book_title": "Test Novel"}, {"volume_no": 2, "planned_chapters": 2}, 6, ""),
    ]


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
