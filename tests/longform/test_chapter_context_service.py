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

    assert {
        key: result[key]
        for key in ("outline", "previous_summary", "characters", "timeline", "foreshadow")
    } == {
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
    assert result["story_bible"] == {}
    assert result["plot_threads"] == []
    assert result["locations"] == []
    assert result["organizations"] == []
    assert result["style_guide"] == {}
    assert result["scenes"] == []
    assert result["context_audit"]["selected"]["characters"] == [
        {"name": "Lin Yue", "reason": "legacy_valid_character"}
    ]


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


def test_build_chapter_context_reads_enhanced_agent_state_with_audit() -> None:
    result = build_chapter_context(
        chapter_no=3,
        outline={"title": "Test Outline", "theme": "loyalty"},
        previous_summary="Chapter two summary.",
        characters=[
            {"name": "Lin Yue", "role": "protagonist", "appearance_chapters": [3]},
            {"name": "Distant Elder", "role": "mentor"},
        ],
        timeline=[],
        foreshadow=[],
        chapter_plan={
            "chapter_no": 3,
            "title": "North Gate Test",
            "goal": "Lin Yue confronts the Night Office at North Gate.",
        },
        story_bible={
            "version": 1,
            "world": {"name": "Mirror City"},
            "rules": ["Mirrors remember vows."],
            "characters": [{"name": "too verbose"}],
        },
        plot_threads={
            "threads": [
                {"id": "main", "summary": "Night Office pressure", "status": "active"},
                {"id": "done", "summary": "Resolved thread", "status": "resolved"},
            ]
        },
        locations={
            "locations": [
                {"name": "North Gate", "description": "Cold checkpoint"},
                {"name": "South Well", "description": "Not relevant"},
            ]
        },
        organizations={
            "organizations": [
                {"name": "Night Office", "goals": ["Control the city"]},
                {"name": "Distant Guild", "goals": ["Wait"]},
            ]
        },
        style_guide={"version": 1, "voice": "restrained"},
        scenes={"scenes": [{"id": "ch003-sc001", "chapter_no": 3, "goal": "Open"}]},
    )

    assert result["characters"] == [
        {
            "name": "Lin Yue",
            "role": "protagonist",
            "traits": [],
            "current_state": "",
        }
    ]
    assert result["story_bible"] == {
        "version": 1,
        "world": {"name": "Mirror City"},
        "rules": ["Mirrors remember vows."],
    }
    assert result["plot_threads"] == [
        {"id": "main", "summary": "Night Office pressure", "status": "active"}
    ]
    assert result["locations"] == [
        {"name": "North Gate", "description": "Cold checkpoint"}
    ]
    assert result["organizations"] == [
        {"name": "Night Office", "goals": ["Control the city"]}
    ]
    assert result["style_guide"] == {"version": 1, "voice": "restrained"}
    assert result["scenes"] == [
        {"id": "ch003-sc001", "chapter_no": 3, "goal": "Open"}
    ]
    assert result["context_audit"]["selection_basis"] == "chapter_plan_and_outline_text"
    assert result["context_audit"]["selected"]["locations"] == [
        {"id": "North Gate", "reason": "task_reference"}
    ]


def test_build_chapter_context_prioritizes_references_over_earlier_active_items() -> None:
    result = build_chapter_context(
        chapter_no=4,
        outline={"title": "Test Outline"},
        previous_summary="",
        characters=[],
        timeline=[],
        foreshadow=[],
        chapter_plan={
            "chapter_no": 4,
            "title": "North Gate Breakthrough",
            "goal": "Resolve the hidden city gate pressure.",
        },
        locations={
            "locations": [
                {"name": f"Active Location {index}", "status": "active"}
                for index in range(1, 7)
            ]
            + [
                {
                    "name": "North Gate",
                    "description": "Relevant late location",
                }
            ]
        },
        plot_threads={
            "threads": [
                {"id": f"active-thread-{index}", "status": "active"}
                for index in range(1, 7)
            ]
            + [
                {
                    "id": "late-chapter-thread",
                    "summary": "Relevant chapter thread",
                    "related_chapters": [4],
                }
            ]
        },
    )

    assert "North Gate" in [item["name"] for item in result["locations"]]
    assert "Active Location 6" not in [item["name"] for item in result["locations"]]
    assert result["context_audit"]["selected"]["locations"][0] == {
        "id": "North Gate",
        "reason": "task_reference",
    }

    assert "late-chapter-thread" in [item["id"] for item in result["plot_threads"]]
    assert "active-thread-6" not in [item["id"] for item in result["plot_threads"]]
    assert result["context_audit"]["selected"]["plot_threads"][0] == {
        "id": "late-chapter-thread",
        "reason": "chapter_reference",
    }


def test_build_chapter_context_does_not_include_unmatched_characters_when_plan_exists() -> None:
    result = build_chapter_context(
        chapter_no=5,
        outline={"title": "Test Outline"},
        previous_summary="",
        characters=[
            {"name": "Lin Yue", "role": "protagonist"},
            {"name": "Distant Elder", "role": "mentor"},
            {"name": "Chapter Witness", "role": "witness", "appearance_chapters": [5]},
        ],
        timeline=[],
        foreshadow=[],
        chapter_plan={
            "chapter_no": 5,
            "title": "Lin Yue Makes a Choice",
            "goal": "Lin Yue and Chapter Witness face the consequence.",
        },
    )

    assert [item["name"] for item in result["characters"]] == [
        "Lin Yue",
        "Chapter Witness",
    ]
    assert result["context_audit"]["selected"]["characters"] == [
        {"name": "Lin Yue", "reason": "task_reference"},
        {"name": "Chapter Witness", "reason": "chapter_reference"},
    ]
