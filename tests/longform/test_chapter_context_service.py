from __future__ import annotations

from core.longform.chapter_context_service import build_chapter_context


def test_build_chapter_context_returns_stable_package_for_chapter_one() -> None:
    result = build_chapter_context(
        chapter_no=1,
        outline={"title": "Test Outline"},
        previous_summary="",
        characters=[
            {
                "name": "Lin Yue",
                "role": "protagonist",
                "traits": ["calm", "careful"],
                "current_state": "Still hiding his strength.",
                "ignored": "not included",
            },
            {"name": "", "role": "invalid"},
            "not-a-dict",
        ],
        timeline=[
            {"chapter_no": 0, "event": "Prologue event"},
            {"chapter_no": 1, "event": "Current chapter event"},
            {"chapter_no": 2, "event": "Future event"},
        ],
        foreshadow=[
            {"id": "fs-1", "content": "Open clue", "status": "open"},
            {"id": "fs-2", "content": "Resolved clue", "status": "resolved"},
            "not-a-dict",
        ],
    )

    assert result == {
        "outline": {"title": "Test Outline"},
        "previous_summary": "",
        "characters": [
            {
                "name": "Lin Yue",
                "role": "protagonist",
                "traits": ["calm", "careful"],
                "current_state": "Still hiding his strength.",
            }
        ],
        "timeline": [{"chapter_no": 0, "event": "Prologue event"}],
        "foreshadow": [{"id": "fs-1", "content": "Open clue", "status": "open"}],
    }


def test_build_chapter_context_keeps_missing_previous_summary_as_empty_string() -> None:
    result = build_chapter_context(
        chapter_no=3,
        outline={"title": "Test Outline"},
        previous_summary="",
        characters=[],
        timeline=[],
        foreshadow=[],
    )

    assert result["previous_summary"] == ""
    assert result["characters"] == []
    assert result["timeline"] == []
    assert result["foreshadow"] == []


def test_build_chapter_context_keeps_only_recent_historical_timeline_events() -> None:
    result = build_chapter_context(
        chapter_no=7,
        outline={"title": "Test Outline"},
        previous_summary="summary",
        characters=[],
        timeline=[
            {"chapter_no": 1, "event": "Event 1"},
            {"chapter_no": 2, "event": "Event 2"},
            {"chapter_no": 3, "event": "Event 3"},
            {"chapter_no": 4, "event": "Event 4"},
            {"chapter_no": 5, "event": "Event 5"},
            {"chapter_no": 6, "event": "Event 6"},
            {"chapter_no": 7, "event": "Current chapter event"},
            {"chapter_no": 8, "event": "Future event"},
        ],
        foreshadow=[],
    )

    assert result["timeline"] == [
        {"chapter_no": 2, "event": "Event 2"},
        {"chapter_no": 3, "event": "Event 3"},
        {"chapter_no": 4, "event": "Event 4"},
        {"chapter_no": 5, "event": "Event 5"},
        {"chapter_no": 6, "event": "Event 6"},
    ]


def test_build_chapter_context_keeps_only_open_foreshadow_items() -> None:
    result = build_chapter_context(
        chapter_no=4,
        outline={"title": "Test Outline"},
        previous_summary="summary",
        characters=[],
        timeline=[],
        foreshadow=[
            {"id": "fs-1", "content": "Open clue", "status": "open"},
            {"id": "fs-2", "content": "Resolved clue", "status": "resolved"},
            {"id": "fs-3", "content": "Hidden clue", "status": "hidden"},
        ],
    )

    assert result["foreshadow"] == [
        {"id": "fs-1", "content": "Open clue", "status": "open"}
    ]
