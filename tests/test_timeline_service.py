from __future__ import annotations

from pathlib import Path

import pytest

from core.timeline_service import (
    TimelineConflictError,
    TimelineValidationError,
    add_timeline_event,
    get_events_by_chapter,
    load_timeline,
    save_timeline,
)


def test_save_and_load_timeline(tmp_path: Path) -> None:
    file_path = tmp_path / "timeline.json"
    expected = [
        {"id": "evt-1", "chapter_no": 1, "event": "Lin Yue arrives in the capital."},
        {"id": "evt-2", "chapter_no": 2, "event": "The hidden letter is discovered."},
    ]

    save_timeline(expected, str(file_path))

    assert load_timeline(str(file_path)) == expected


def test_get_events_by_chapter_returns_matching_events(tmp_path: Path) -> None:
    file_path = tmp_path / "timeline.json"
    save_timeline(
        [
            {"id": "evt-1", "chapter_no": 1, "event": "Opening escape."},
            {"id": "evt-2", "chapter_no": 2, "event": "A witness appears."},
            {"id": "evt-3", "chapter_no": 2, "event": "The clue changes hands."},
        ],
        str(file_path),
    )

    result = get_events_by_chapter(2, str(file_path))

    assert result == [
        {"id": "evt-2", "chapter_no": 2, "event": "A witness appears."},
        {"id": "evt-3", "chapter_no": 2, "event": "The clue changes hands."},
    ]


def test_add_timeline_event_raises_for_missing_required_fields(tmp_path: Path) -> None:
    file_path = tmp_path / "timeline.json"

    with pytest.raises(
        TimelineValidationError,
        match="missing required field\\(s\\): event",
    ):
        add_timeline_event({"id": "evt-1", "chapter_no": 1}, str(file_path))


def test_add_timeline_event_raises_for_duplicate_id(tmp_path: Path) -> None:
    file_path = tmp_path / "timeline.json"
    add_timeline_event(
        {"id": "evt-1", "chapter_no": 1, "event": "Opening escape."},
        str(file_path),
    )

    with pytest.raises(
        TimelineConflictError,
        match="Timeline event with id 'evt-1' already exists",
    ):
        add_timeline_event(
            {"id": "evt-1", "chapter_no": 2, "event": "A conflicting record."},
            str(file_path),
        )


def test_timeline_service_supports_project_root_path(tmp_path: Path) -> None:
    project_root = tmp_path / "novel-project"

    add_timeline_event(
        {"id": "evt-1", "chapter_no": 1, "event": "Opening escape."},
        str(project_root),
    )

    assert load_timeline(str(project_root)) == [
        {"id": "evt-1", "chapter_no": 1, "event": "Opening escape."}
    ]
    assert get_events_by_chapter(1, str(project_root)) == [
        {"id": "evt-1", "chapter_no": 1, "event": "Opening escape."}
    ]
