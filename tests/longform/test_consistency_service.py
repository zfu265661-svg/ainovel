from __future__ import annotations

from pathlib import Path

import pytest

from core.longform.consistency_service import run_review_consistency_check
from core.longform.project_state_repository import get_chapter_review_path
from core.longform.review_service import create_or_refresh_review
from core.project_service import create_project_structure, get_chapter_suggestion_path
from core.storage import load_json, save_json


def test_run_review_consistency_check_adds_blocker_for_blank_normalized_update_field(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "consistency-project"
    create_project_structure(
        str(project_root),
        title="Test Novel",
        topic="xianxia",
        style="cold",
        target="serial",
    )
    save_json(
        get_chapter_suggestion_path(str(project_root), 1),
        {
            "chapter_no": 1,
            "character_updates": [],
            "timeline_updates": [
                {"action": " add ", "target": " chapter_1 ", "content": "   "}
            ],
            "foreshadow_updates": [],
            "notes": "suggestion",
        },
    )
    create_or_refresh_review(str(project_root), 1)
    monkeypatch.setattr(
        "core.longform.consistency_service._utc_now_iso",
        lambda: "2026-03-28T12:10:00Z",
    )

    review = run_review_consistency_check(str(project_root), 1)

    assert review["consistency_check"] == {
        "version": 1,
        "checked_at": "2026-03-28T12:10:00Z",
        "blockers": [
            {
                "code": "blank_update_field",
                "message": (
                    "approved_suggestion.timeline_updates[0].content must be non-empty."
                ),
                "field": "approved_suggestion.timeline_updates[0].content",
            }
        ],
        "warnings": [],
    }


def test_run_review_consistency_check_adds_blocker_for_normalized_internal_timeline_duplicate(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "consistency-project"
    create_project_structure(
        str(project_root),
        title="Test Novel",
        topic="xianxia",
        style="cold",
        target="serial",
    )
    save_json(
        get_chapter_suggestion_path(str(project_root), 1),
        {
            "chapter_no": 1,
            "character_updates": [],
            "timeline_updates": [
                {"action": " add", "target": "chapter_1 ", "content": "Event opens."},
                {"action": "add ", "target": " chapter_1", "content": " Event opens. "},
            ],
            "foreshadow_updates": [],
            "notes": "suggestion",
        },
    )
    create_or_refresh_review(str(project_root), 1)
    monkeypatch.setattr(
        "core.longform.consistency_service._utc_now_iso",
        lambda: "2026-03-28T12:11:00Z",
    )

    review = run_review_consistency_check(str(project_root), 1)

    assert review["consistency_check"]["checked_at"] == "2026-03-28T12:11:00Z"
    assert review["consistency_check"]["warnings"] == []
    assert review["consistency_check"]["blockers"] == [
        {
            "code": "duplicate_timeline_update",
            "message": (
                "approved_suggestion.timeline_updates[1] duplicates a timeline entry for chapter 1."
            ),
            "field": "approved_suggestion.timeline_updates[1]",
        }
    ]


def test_run_review_consistency_check_adds_blocker_for_existing_timeline_duplicate(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "consistency-project"
    create_project_structure(
        str(project_root),
        title="Test Novel",
        topic="xianxia",
        style="cold",
        target="serial",
    )
    save_json(
        str(project_root / "timeline.json"),
        {
            "events": [
                {
                    "chapter_no": 2,
                    "action": "add",
                    "target": "chapter_2",
                    "event": "Conflict escalates.",
                }
            ]
        },
    )
    save_json(
        get_chapter_suggestion_path(str(project_root), 2),
        {
            "chapter_no": 2,
            "character_updates": [],
            "timeline_updates": [
                {
                    "action": " add ",
                    "target": " chapter_2 ",
                    "content": " Conflict escalates. ",
                }
            ],
            "foreshadow_updates": [],
            "notes": "suggestion",
        },
    )
    create_or_refresh_review(str(project_root), 2)
    monkeypatch.setattr(
        "core.longform.consistency_service._utc_now_iso",
        lambda: "2026-03-28T12:12:00Z",
    )

    review = run_review_consistency_check(str(project_root), 2)

    assert review["consistency_check"]["checked_at"] == "2026-03-28T12:12:00Z"
    assert review["consistency_check"]["warnings"] == [
        {
            "code": "previous_summary_missing",
            "message": "Previous chapter summary is missing for chapter 2.",
            "field": "previous_summary",
        }
    ]
    assert review["consistency_check"]["blockers"] == [
        {
            "code": "duplicate_timeline_update",
            "message": (
                "approved_suggestion.timeline_updates[0] duplicates a timeline entry for chapter 2."
            ),
            "field": "approved_suggestion.timeline_updates[0]",
        }
    ]


def test_run_review_consistency_check_skips_dirty_history_entries_without_crashing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "consistency-project"
    create_project_structure(
        str(project_root),
        title="Test Novel",
        topic="xianxia",
        style="cold",
        target="serial",
    )
    save_json(
        str(project_root / "timeline.json"),
        {
            "events": [
                {"chapter_no": 2, "action": "add"},
                {"chapter_no": "2", "action": "add", "target": "chapter_2", "event": "bad"},
                "not-an-object",
            ]
        },
    )
    save_json(
        get_chapter_suggestion_path(str(project_root), 2),
        {
            "chapter_no": 2,
            "character_updates": [],
            "timeline_updates": [
                {
                    "action": "add",
                    "target": "chapter_2",
                    "content": "Fresh event.",
                }
            ],
            "foreshadow_updates": [],
            "notes": "suggestion",
        },
    )
    create_or_refresh_review(str(project_root), 2)
    monkeypatch.setattr(
        "core.longform.consistency_service._utc_now_iso",
        lambda: "2026-03-28T12:13:00Z",
    )

    review = run_review_consistency_check(str(project_root), 2)

    assert review["consistency_check"]["checked_at"] == "2026-03-28T12:13:00Z"
    assert review["consistency_check"]["blockers"] == []
    assert review["consistency_check"]["warnings"] == [
        {
            "code": "previous_summary_missing",
            "message": "Previous chapter summary is missing for chapter 2.",
            "field": "previous_summary",
        }
    ]


def test_run_review_consistency_check_adds_warning_for_missing_previous_summary(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "consistency-project"
    create_project_structure(
        str(project_root),
        title="Test Novel",
        topic="xianxia",
        style="cold",
        target="serial",
    )
    save_json(
        get_chapter_suggestion_path(str(project_root), 2),
        {
            "chapter_no": 2,
            "character_updates": [],
            "timeline_updates": [],
            "foreshadow_updates": [],
            "notes": "suggestion",
        },
    )
    create_or_refresh_review(str(project_root), 2)
    monkeypatch.setattr(
        "core.longform.consistency_service._utc_now_iso",
        lambda: "2026-03-28T12:14:00Z",
    )

    review = run_review_consistency_check(str(project_root), 2)

    assert review["consistency_check"]["blockers"] == []
    assert review["consistency_check"]["warnings"] == [
        {
            "code": "previous_summary_missing",
            "message": "Previous chapter summary is missing for chapter 2.",
            "field": "previous_summary",
        }
    ]


def test_run_review_consistency_check_adds_warning_for_repeated_normalized_character_targets(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "consistency-project"
    create_project_structure(
        str(project_root),
        title="Test Novel",
        topic="xianxia",
        style="cold",
        target="serial",
    )
    save_json(
        get_chapter_suggestion_path(str(project_root), 1),
        {
            "chapter_no": 1,
            "character_updates": [
                {"action": "update", "target": " Lin Yue ", "content": "First"},
                {"action": "update", "target": "Lin Yue", "content": "Second"},
            ],
            "timeline_updates": [],
            "foreshadow_updates": [],
            "notes": "suggestion",
        },
    )
    create_or_refresh_review(str(project_root), 1)
    monkeypatch.setattr(
        "core.longform.consistency_service._utc_now_iso",
        lambda: "2026-03-28T12:15:00Z",
    )

    review = run_review_consistency_check(str(project_root), 1)

    assert review["consistency_check"]["blockers"] == []
    assert review["consistency_check"]["warnings"] == [
        {
            "code": "duplicate_character_target",
            "message": "approved_suggestion.character_updates repeats target 'Lin Yue'.",
            "field": "approved_suggestion.character_updates",
        }
    ]


def test_run_review_consistency_check_adds_warning_for_repeated_normalized_foreshadow_targets(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "consistency-project"
    create_project_structure(
        str(project_root),
        title="Test Novel",
        topic="xianxia",
        style="cold",
        target="serial",
    )
    save_json(
        get_chapter_suggestion_path(str(project_root), 1),
        {
            "chapter_no": 1,
            "character_updates": [],
            "timeline_updates": [],
            "foreshadow_updates": [
                {"action": "add", "target": " fs-1 ", "content": "First"},
                {"action": "update", "target": "fs-1", "content": "Second"},
            ],
            "notes": "suggestion",
        },
    )
    create_or_refresh_review(str(project_root), 1)
    monkeypatch.setattr(
        "core.longform.consistency_service._utc_now_iso",
        lambda: "2026-03-28T12:16:00Z",
    )

    review = run_review_consistency_check(str(project_root), 1)

    assert review["consistency_check"]["blockers"] == []
    assert review["consistency_check"]["warnings"] == [
        {
            "code": "duplicate_foreshadow_target",
            "message": "approved_suggestion.foreshadow_updates repeats target 'fs-1'.",
            "field": "approved_suggestion.foreshadow_updates",
        }
    ]


def test_run_review_consistency_check_keeps_committed_review_checked_at_unchanged(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "consistency-project"
    create_project_structure(
        str(project_root),
        title="Test Novel",
        topic="xianxia",
        style="cold",
        target="serial",
    )
    suggestion_path = get_chapter_suggestion_path(str(project_root), 1)
    review_path = get_chapter_review_path(str(project_root), 1)
    save_json(
        suggestion_path,
        {
            "chapter_no": 1,
            "character_updates": [],
            "timeline_updates": [],
            "foreshadow_updates": [],
            "notes": "suggestion",
        },
    )
    create_or_refresh_review(str(project_root), 1)
    monkeypatch.setattr(
        "core.longform.consistency_service._utc_now_iso",
        lambda: "2026-03-28T12:17:00Z",
    )
    run_review_consistency_check(str(project_root), 1)

    review = load_json(review_path)
    save_json(
        review_path,
        {
            **review,
            "committed": True,
            "committed_chapter_no": 1,
        },
    )
    monkeypatch.setattr(
        "core.longform.consistency_service._utc_now_iso",
        lambda: "2026-03-28T12:18:00Z",
    )

    unchanged_review = run_review_consistency_check(str(project_root), 1)

    assert unchanged_review["consistency_check"]["checked_at"] == "2026-03-28T12:17:00Z"
    assert load_json(review_path)["consistency_check"]["checked_at"] == "2026-03-28T12:17:00Z"
