from __future__ import annotations

from pathlib import Path

import pytest

from core.longform.project_state_repository import get_chapter_review_path
from core.longform.review_service import (
    create_or_refresh_review,
    load_review_for_commit,
)
from core.project_service import create_project_structure, get_chapter_suggestion_path
from core.storage import load_json, save_json


def _consistency_check(
    *,
    blockers: list[dict[str, object]] | None = None,
    warnings: list[dict[str, object]] | None = None,
    checked_at: str = "2026-03-28T12:00:00Z",
) -> dict[str, object]:
    return {
        "version": 1,
        "checked_at": checked_at,
        "blockers": blockers or [],
        "warnings": warnings or [],
    }


def test_create_or_refresh_review_creates_review_from_canonical_suggestion(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "review-project"
    create_project_structure(
        str(project_root),
        title="Test Novel",
        topic="xianxia",
        style="cold",
        target="serial",
    )
    suggestion_path = get_chapter_suggestion_path(str(project_root), 1)
    save_json(
        suggestion_path,
        {
            "chapter_no": 1,
            "character_updates": [],
            "timeline_updates": [],
            "foreshadow_updates": [],
            "notes": "first suggestion",
        },
    )
    monkeypatch.setattr(
        "core.longform.review_service._utc_now_iso",
        lambda: "2026-03-28T12:00:00Z",
    )

    review = create_or_refresh_review(str(project_root), 1)

    assert review == {
        "version": 1,
        "chapter_no": 1,
        "created_at": "2026-03-28T12:00:00Z",
        "suggestion_path": suggestion_path,
        "approved_suggestion": {
            "chapter_no": 1,
            "character_updates": [],
            "timeline_updates": [],
            "foreshadow_updates": [],
            "notes": "first suggestion",
        },
        "committed": False,
        "committed_chapter_no": None,
    }
    assert load_json(get_chapter_review_path(str(project_root), 1)) == review


def test_create_or_refresh_review_refreshes_from_current_disk_suggestion_and_rewrites_created_at(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "review-project"
    create_project_structure(
        str(project_root),
        title="Test Novel",
        topic="xianxia",
        style="cold",
        target="serial",
    )
    suggestion_path = get_chapter_suggestion_path(str(project_root), 1)
    save_json(
        suggestion_path,
        {
            "chapter_no": 1,
            "character_updates": [],
            "timeline_updates": [],
            "foreshadow_updates": [],
            "notes": "first suggestion",
        },
    )
    monkeypatch.setattr(
        "core.longform.review_service._utc_now_iso",
        lambda: "2026-03-28T12:00:00Z",
    )
    create_or_refresh_review(str(project_root), 1)

    save_json(
        suggestion_path,
        {
            "chapter_no": 1,
            "character_updates": [
                {"action": "update", "target": "Lin Yue", "content": "Changed on disk."}
            ],
            "timeline_updates": [],
            "foreshadow_updates": [],
            "notes": "second suggestion",
        },
    )
    monkeypatch.setattr(
        "core.longform.review_service._utc_now_iso",
        lambda: "2026-03-28T12:05:00Z",
    )

    review = create_or_refresh_review(str(project_root), 1)

    assert review["created_at"] == "2026-03-28T12:05:00Z"
    assert review["approved_suggestion"] == {
        "chapter_no": 1,
        "character_updates": [
            {"action": "update", "target": "Lin Yue", "content": "Changed on disk."}
        ],
        "timeline_updates": [],
        "foreshadow_updates": [],
        "notes": "second suggestion",
    }


def test_create_or_refresh_review_rejects_refresh_for_committed_review_and_keeps_created_at(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "review-project"
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
            "notes": "first suggestion",
        },
    )
    monkeypatch.setattr(
        "core.longform.review_service._utc_now_iso",
        lambda: "2026-03-28T12:00:00Z",
    )
    create_or_refresh_review(str(project_root), 1)

    review = load_json(review_path)
    save_json(
        review_path,
        {
            **review,
            "committed": True,
            "committed_chapter_no": 1,
        },
    )
    save_json(
        suggestion_path,
        {
            "chapter_no": 1,
            "character_updates": [],
            "timeline_updates": [],
            "foreshadow_updates": [],
            "notes": "second suggestion",
        },
    )
    monkeypatch.setattr(
        "core.longform.review_service._utc_now_iso",
        lambda: "2026-03-28T12:10:00Z",
    )

    with pytest.raises(ValueError, match="already been committed"):
        create_or_refresh_review(str(project_root), 1)

    refreshed = load_json(review_path)
    assert refreshed["created_at"] == "2026-03-28T12:00:00Z"
    assert refreshed["committed"] is True


def test_load_review_for_commit_rejects_review_chapter_mismatch(tmp_path: Path) -> None:
    project_root = tmp_path / "review-project"
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
    save_json(
        review_path,
        {
            "version": 1,
            "chapter_no": 2,
            "created_at": "2026-03-28T12:00:00Z",
            "suggestion_path": suggestion_path,
            "approved_suggestion": {
                "chapter_no": 2,
                "character_updates": [],
                "timeline_updates": [],
                "foreshadow_updates": [],
                "notes": "suggestion",
            },
            "consistency_check": _consistency_check(),
            "committed": False,
            "committed_chapter_no": None,
        },
    )

    with pytest.raises(ValueError, match="Review chapter_no mismatch"):
        load_review_for_commit(str(project_root), 1)


def test_load_review_for_commit_rejects_approved_suggestion_chapter_mismatch(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "review-project"
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
    save_json(
        review_path,
        {
            "version": 1,
            "chapter_no": 1,
            "created_at": "2026-03-28T12:00:00Z",
            "suggestion_path": suggestion_path,
            "approved_suggestion": {
                "chapter_no": 2,
                "character_updates": [],
                "timeline_updates": [],
                "foreshadow_updates": [],
                "notes": "suggestion",
            },
            "consistency_check": _consistency_check(),
            "committed": False,
            "committed_chapter_no": None,
        },
    )

    with pytest.raises(ValueError, match="approved_suggestion.chapter_no"):
        load_review_for_commit(str(project_root), 1)


def test_load_review_for_commit_rejects_committed_review(tmp_path: Path) -> None:
    project_root = tmp_path / "review-project"
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
    save_json(
        review_path,
        {
            "version": 1,
            "chapter_no": 1,
            "created_at": "2026-03-28T12:00:00Z",
            "suggestion_path": suggestion_path,
            "approved_suggestion": {
                "chapter_no": 1,
                "character_updates": [],
                "timeline_updates": [],
                "foreshadow_updates": [],
                "notes": "suggestion",
            },
            "consistency_check": _consistency_check(),
            "committed": True,
            "committed_chapter_no": 1,
        },
    )

    with pytest.raises(ValueError, match="already been committed"):
        load_review_for_commit(str(project_root), 1)


def test_load_review_for_commit_rejects_missing_consistency_check(tmp_path: Path) -> None:
    project_root = tmp_path / "review-project"
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
    save_json(
        review_path,
        {
            "version": 1,
            "chapter_no": 1,
            "created_at": "2026-03-28T12:00:00Z",
            "suggestion_path": suggestion_path,
            "approved_suggestion": {
                "chapter_no": 1,
                "character_updates": [],
                "timeline_updates": [],
                "foreshadow_updates": [],
                "notes": "suggestion",
            },
            "committed": False,
            "committed_chapter_no": None,
        },
    )

    with pytest.raises(ValueError, match="consistency_check"):
        load_review_for_commit(str(project_root), 1)


def test_load_review_for_commit_rejects_review_with_blockers(tmp_path: Path) -> None:
    project_root = tmp_path / "review-project"
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
    save_json(
        review_path,
        {
            "version": 1,
            "chapter_no": 1,
            "created_at": "2026-03-28T12:00:00Z",
            "suggestion_path": suggestion_path,
            "approved_suggestion": {
                "chapter_no": 1,
                "character_updates": [],
                "timeline_updates": [],
                "foreshadow_updates": [],
                "notes": "suggestion",
            },
            "consistency_check": _consistency_check(
                blockers=[
                    {
                        "code": "blank_update_field",
                        "message": "bad field",
                        "field": "approved_suggestion.timeline_updates[0].content",
                    }
                ]
            ),
            "committed": False,
            "committed_chapter_no": None,
        },
    )

    with pytest.raises(ValueError, match="contains blocker"):
        load_review_for_commit(str(project_root), 1)


def test_load_review_for_commit_allows_warning_only_review(tmp_path: Path) -> None:
    project_root = tmp_path / "review-project"
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
    save_json(
        review_path,
        {
            "version": 1,
            "chapter_no": 1,
            "created_at": "2026-03-28T12:00:00Z",
            "suggestion_path": suggestion_path,
            "approved_suggestion": {
                "chapter_no": 1,
                "character_updates": [],
                "timeline_updates": [],
                "foreshadow_updates": [],
                "notes": "suggestion",
            },
            "consistency_check": _consistency_check(
                warnings=[
                    {
                        "code": "previous_summary_missing",
                        "message": "warning only",
                        "field": "previous_summary",
                    }
                ]
            ),
            "committed": False,
            "committed_chapter_no": None,
        },
    )

    review = load_review_for_commit(str(project_root), 1)

    assert review["consistency_check"]["warnings"] == [
        {
            "code": "previous_summary_missing",
            "message": "warning only",
            "field": "previous_summary",
        }
    ]
