from __future__ import annotations

from pathlib import Path

import pytest

from core.longform.project_state_repository import get_chapter_review_path
from core.longform.review_service import (
    approve_review,
    assert_review_can_commit,
    list_reviews,
    load_review_for_display,
    prepare_review,
    reject_review,
)
from core.project_service import create_project_structure, get_chapter_suggestion_path
from core.storage import load_json, save_json
from core.workflow_service import commit_approved_review


def test_list_reviews_reports_pending_and_committed_reviews(tmp_path: Path) -> None:
    project_root = _create_project(tmp_path)
    _save_suggestion(project_root, 1)
    _save_review(project_root, 1, committed=False)
    _save_suggestion(project_root, 2)
    _save_review(project_root, 2, committed=True)

    reviews = list_reviews(str(project_root))

    assert reviews == [
        {
            "chapter_no": 1,
            "status": "pending",
            "has_consistency_check": True,
            "committed": False,
            "review_path": get_chapter_review_path(str(project_root), 1),
        },
        {
            "chapter_no": 2,
            "status": "committed",
            "has_consistency_check": True,
            "committed": True,
            "review_path": get_chapter_review_path(str(project_root), 2),
        },
    ]


def test_load_review_for_display_returns_normalized_status_and_suggestion_summary(
    tmp_path: Path,
) -> None:
    project_root = _create_project(tmp_path)
    _save_suggestion(project_root, 1)
    _save_review(
        project_root,
        1,
        committed=False,
        suggestion={
            "chapter_no": 1,
            "character_updates": [
                {"action": "update", "target": "Lin Yue", "content": "Ready."}
            ],
            "timeline_updates": [
                {"action": "add", "target": "chapter_1", "content": "Event."}
            ],
            "foreshadow_updates": [],
            "notes": "Review summary.",
        },
    )

    report = load_review_for_display(str(project_root), 1)

    assert report["status"] == "pending"
    assert report["approved_suggestion_summary"] == {
        "chapter_no": 1,
        "character_updates": 1,
        "timeline_updates": 1,
        "foreshadow_updates": 0,
        "notes": "Review summary.",
    }
    assert report["review_notes"] == []


def test_pending_review_can_be_approved_without_mutating_formal_state(
    tmp_path: Path,
) -> None:
    project_root = _create_project(tmp_path)
    _save_suggestion(project_root, 1)
    prepare_review(str(project_root), 1)
    formal_state_before = _load_formal_state(project_root)

    approved = approve_review(str(project_root), 1)

    assert approved["status"] == "approved"
    assert approved["approved_at"]
    assert _load_formal_state(project_root) == formal_state_before
    assert assert_review_can_commit(str(project_root), 1)["status"] == "approved"


def test_pending_review_can_be_rejected_with_reason_without_mutating_formal_state(
    tmp_path: Path,
) -> None:
    project_root = _create_project(tmp_path)
    _save_suggestion(project_root, 1)
    prepare_review(str(project_root), 1)
    formal_state_before = _load_formal_state(project_root)

    rejected = reject_review(str(project_root), 1, "Continuity is wrong.")

    assert rejected["status"] == "rejected"
    assert rejected["reject_reason"] == "Continuity is wrong."
    assert rejected["rejected_at"]
    assert _load_formal_state(project_root) == formal_state_before


def test_rejected_review_cannot_commit_approved(tmp_path: Path) -> None:
    project_root = _create_project(tmp_path)
    _save_suggestion(project_root, 1)
    prepare_review(str(project_root), 1)
    reject_review(str(project_root), 1, "Needs rewrite.")

    with pytest.raises(Exception, match="has been rejected"):
        commit_approved_review(str(project_root), 1)


def test_unapproved_review_cannot_commit_approved(tmp_path: Path) -> None:
    project_root = _create_project(tmp_path)
    _save_suggestion(project_root, 1)
    prepare_review(str(project_root), 1)

    with pytest.raises(Exception, match="has not been approved"):
        commit_approved_review(str(project_root), 1)


def test_committed_review_cannot_be_approved_rejected_or_committed_again(
    tmp_path: Path,
) -> None:
    project_root = _create_project(tmp_path)
    _save_suggestion(project_root, 1)
    _save_review(project_root, 1, committed=True)

    with pytest.raises(Exception, match="already been committed"):
        approve_review(str(project_root), 1)
    with pytest.raises(Exception, match="already been committed"):
        reject_review(str(project_root), 1, "Too late.")
    with pytest.raises(Exception, match="already been committed"):
        commit_approved_review(str(project_root), 1)


def test_legacy_review_without_status_falls_back_to_pending_or_committed(
    tmp_path: Path,
) -> None:
    project_root = _create_project(tmp_path)
    _save_suggestion(project_root, 1)
    _save_review(project_root, 1, committed=False)
    _save_suggestion(project_root, 2)
    _save_review(project_root, 2, committed=True)

    assert load_review_for_display(str(project_root), 1)["status"] == "pending"
    assert load_review_for_display(str(project_root), 2)["status"] == "committed"


def test_review_with_consistency_blockers_cannot_be_approved(tmp_path: Path) -> None:
    project_root = _create_project(tmp_path)
    _save_suggestion(
        project_root,
        1,
        timeline_updates=[
            {"action": "add", "target": "chapter_1", "content": "  "}
        ],
    )
    prepare_review(str(project_root), 1)

    with pytest.raises(Exception, match="contains blocker"):
        approve_review(str(project_root), 1)


def _create_project(tmp_path: Path) -> Path:
    project_root = tmp_path / "review-control-project"
    create_project_structure(
        str(project_root),
        title="Review Control Novel",
        topic="xianxia",
        style="cold",
        target="serial",
    )
    save_json(str(project_root / "characters.json"), {"characters": []})
    save_json(str(project_root / "timeline.json"), {"events": []})
    save_json(str(project_root / "foreshadow.json"), {"items": []})
    return project_root


def _save_suggestion(
    project_root: Path,
    chapter_no: int,
    *,
    character_updates: list[dict[str, object]] | None = None,
    timeline_updates: list[dict[str, object]] | None = None,
    foreshadow_updates: list[dict[str, object]] | None = None,
) -> None:
    save_json(
        get_chapter_suggestion_path(str(project_root), chapter_no),
        {
            "chapter_no": chapter_no,
            "character_updates": character_updates or [],
            "timeline_updates": timeline_updates or [],
            "foreshadow_updates": foreshadow_updates or [],
            "notes": "Suggestion only.",
        },
    )


def _save_review(
    project_root: Path,
    chapter_no: int,
    *,
    committed: bool,
    suggestion: dict[str, object] | None = None,
) -> None:
    suggestion_path = get_chapter_suggestion_path(str(project_root), chapter_no)
    save_json(
        get_chapter_review_path(str(project_root), chapter_no),
        {
            "version": 1,
            "chapter_no": chapter_no,
            "created_at": "2026-03-28T12:00:00Z",
            "suggestion_path": suggestion_path,
            "approved_suggestion": suggestion
            or {
                "chapter_no": chapter_no,
                "character_updates": [],
                "timeline_updates": [],
                "foreshadow_updates": [],
                "notes": "Suggestion only.",
            },
            "consistency_check": {
                "version": 1,
                "checked_at": "2026-03-28T12:01:00Z",
                "blockers": [],
                "warnings": [],
            },
            "committed": committed,
            "committed_chapter_no": chapter_no if committed else None,
        },
    )


def _load_formal_state(project_root: Path) -> dict[str, object]:
    return {
        "characters": load_json(str(project_root / "characters.json")),
        "timeline": load_json(str(project_root / "timeline.json")),
        "foreshadow": load_json(str(project_root / "foreshadow.json")),
    }
