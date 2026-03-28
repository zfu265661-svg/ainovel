from __future__ import annotations

from pathlib import Path

import pytest

from core.longform.project_state_repository import (
    get_chapter_review_path,
    get_chapter_snapshot_path,
)
from core.longform.snapshot_service import (
    create_pending_snapshot,
    handle_preflight_snapshot,
)
from core.project_service import create_project_structure, get_chapter_suggestion_path
from core.storage import load_json, save_json


def _review_payload(project_root: Path, chapter_no: int, committed: bool) -> dict[str, object]:
    return {
        "version": 1,
        "chapter_no": chapter_no,
        "created_at": "2026-03-28T12:00:00Z",
        "suggestion_path": str(project_root / "suggestions" / f"ch{chapter_no:03d}.suggestion.json"),
        "approved_suggestion": {
            "chapter_no": chapter_no,
            "character_updates": [
                {"action": "update", "target": "Lin Yue", "content": "Changed."}
            ],
            "timeline_updates": [
                {"action": "add", "target": f"chapter_{chapter_no}", "content": "Event."}
            ],
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
    }


def _suggestion_payload(chapter_no: int, committed: bool) -> dict[str, object]:
    payload: dict[str, object] = {
        "chapter_no": chapter_no,
        "character_updates": [
            {"action": "update", "target": "Lin Yue", "content": "Changed."}
        ],
        "timeline_updates": [
            {"action": "add", "target": f"chapter_{chapter_no}", "content": "Event."}
        ],
        "foreshadow_updates": [],
        "notes": "Suggestion only.",
    }
    if committed:
        payload["committed"] = True
        payload["committed_chapter_no"] = chapter_no
    return payload


def _state_before() -> dict[str, object]:
    return {
        "characters": {
            "characters": [],
            "meta": {"source": "before"},
        },
        "timeline": {
            "events": [],
            "meta": {"source": "before"},
        },
        "foreshadow": {
            "items": [],
            "meta": {"source": "before"},
        },
    }


def test_create_pending_snapshot_saves_full_state_before_payloads_verbatim(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "snapshot-project"
    create_project_structure(
        str(project_root),
        title="Test Novel",
        topic="xianxia",
        style="cold",
        target="serial",
    )
    review_path = get_chapter_review_path(str(project_root), 1)
    suggestion_path = get_chapter_suggestion_path(str(project_root), 1)
    state_before = _state_before()
    monkeypatch.setattr(
        "core.longform.snapshot_service._utc_now_iso",
        lambda: "2026-03-28T12:10:00Z",
    )

    snapshot = create_pending_snapshot(
        project_root=str(project_root),
        chapter_no=1,
        review_path=review_path,
        suggestion_path=suggestion_path,
        state_before=state_before,
    )

    assert snapshot == {
        "version": 1,
        "chapter_no": 1,
        "created_at": "2026-03-28T12:10:00Z",
        "status": "pending",
        "review_path": review_path,
        "suggestion_path": suggestion_path,
        "state_before": state_before,
        "restored_at": None,
        "last_error": None,
    }
    assert load_json(get_chapter_snapshot_path(str(project_root), 1)) == snapshot


def test_handle_preflight_snapshot_restores_unfinished_commit_and_cleans_snapshot(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "snapshot-project"
    create_project_structure(
        str(project_root),
        title="Test Novel",
        topic="xianxia",
        style="cold",
        target="serial",
    )
    chapter_no = 1
    snapshot_path = get_chapter_snapshot_path(str(project_root), chapter_no)
    review_path = get_chapter_review_path(str(project_root), chapter_no)
    suggestion_path = get_chapter_suggestion_path(str(project_root), chapter_no)
    state_before = _state_before()
    save_json(str(project_root / "characters.json"), {"characters": [{"name": "Dirty"}]})
    save_json(
        str(project_root / "timeline.json"),
        {"events": [{"chapter_no": 1, "action": "add", "target": "chapter_1", "event": "Dirty"}]},
    )
    save_json(str(project_root / "foreshadow.json"), {"items": [{"id": "fs-1"}]})
    save_json(review_path, _review_payload(project_root, chapter_no, committed=False))
    save_json(suggestion_path, _suggestion_payload(chapter_no, committed=True))
    monkeypatch.setattr(
        "core.longform.snapshot_service._utc_now_iso",
        lambda: "2026-03-28T12:11:00Z",
    )
    create_pending_snapshot(
        project_root=str(project_root),
        chapter_no=chapter_no,
        review_path=review_path,
        suggestion_path=suggestion_path,
        state_before=state_before,
    )

    result = handle_preflight_snapshot(str(project_root), chapter_no)

    assert result == {"status": "restored"}
    assert not Path(snapshot_path).exists()
    assert load_json(str(project_root / "characters.json")) == state_before["characters"]
    assert load_json(str(project_root / "timeline.json")) == state_before["timeline"]
    assert load_json(str(project_root / "foreshadow.json")) == state_before["foreshadow"]
    restored_review = load_json(review_path)
    restored_suggestion = load_json(suggestion_path)
    assert restored_review["committed"] is False
    assert restored_review["committed_chapter_no"] is None
    assert "committed" not in restored_suggestion
    assert "committed_chapter_no" not in restored_suggestion


def test_handle_preflight_snapshot_fails_fast_when_restore_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "snapshot-project"
    create_project_structure(
        str(project_root),
        title="Test Novel",
        topic="xianxia",
        style="cold",
        target="serial",
    )
    chapter_no = 1
    review_path = get_chapter_review_path(str(project_root), chapter_no)
    suggestion_path = get_chapter_suggestion_path(str(project_root), chapter_no)
    save_json(str(project_root / "characters.json"), {"characters": [{"name": "Dirty"}]})
    save_json(str(project_root / "timeline.json"), {"events": []})
    save_json(str(project_root / "foreshadow.json"), {"items": []})
    save_json(review_path, _review_payload(project_root, chapter_no, committed=False))
    save_json(suggestion_path, _suggestion_payload(chapter_no, committed=True))
    create_pending_snapshot(
        project_root=str(project_root),
        chapter_no=chapter_no,
        review_path=review_path,
        suggestion_path=suggestion_path,
        state_before=_state_before(),
    )

    original_save_json = save_json

    def failing_save_json(path: str, data) -> None:
        if path == str(project_root / "characters.json"):
            raise RuntimeError("characters restore failed")
        original_save_json(path, data)

    monkeypatch.setattr("core.longform.snapshot_service.save_json", failing_save_json)

    with pytest.raises(Exception, match="preflight unresolved snapshot restore"):
        handle_preflight_snapshot(str(project_root), chapter_no)

    assert Path(get_chapter_snapshot_path(str(project_root), chapter_no)).exists()


def test_handle_preflight_snapshot_cleans_stale_snapshot_without_restoring_state(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "snapshot-project"
    create_project_structure(
        str(project_root),
        title="Test Novel",
        topic="xianxia",
        style="cold",
        target="serial",
    )
    chapter_no = 1
    snapshot_path = get_chapter_snapshot_path(str(project_root), chapter_no)
    review_path = get_chapter_review_path(str(project_root), chapter_no)
    suggestion_path = get_chapter_suggestion_path(str(project_root), chapter_no)
    committed_characters = {"characters": [{"name": "Lin Yue", "current_state": "Committed"}]}
    save_json(str(project_root / "characters.json"), committed_characters)
    save_json(
        str(project_root / "timeline.json"),
        {"events": [{"chapter_no": 1, "action": "add", "target": "chapter_1", "event": "Committed"}]},
    )
    save_json(str(project_root / "foreshadow.json"), {"items": []})
    save_json(review_path, _review_payload(project_root, chapter_no, committed=True))
    save_json(suggestion_path, _suggestion_payload(chapter_no, committed=True))
    create_pending_snapshot(
        project_root=str(project_root),
        chapter_no=chapter_no,
        review_path=review_path,
        suggestion_path=suggestion_path,
        state_before=_state_before(),
    )

    result = handle_preflight_snapshot(str(project_root), chapter_no)

    assert result == {
        "status": "already_committed",
        "approved_suggestion": _review_payload(project_root, chapter_no, committed=True)["approved_suggestion"],
    }
    assert not Path(snapshot_path).exists()
    assert load_json(str(project_root / "characters.json")) == committed_characters


def test_handle_preflight_snapshot_raises_when_stale_snapshot_cleanup_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "snapshot-project"
    create_project_structure(
        str(project_root),
        title="Test Novel",
        topic="xianxia",
        style="cold",
        target="serial",
    )
    chapter_no = 1
    snapshot_path = get_chapter_snapshot_path(str(project_root), chapter_no)
    review_path = get_chapter_review_path(str(project_root), chapter_no)
    suggestion_path = get_chapter_suggestion_path(str(project_root), chapter_no)
    committed_characters = {"characters": [{"name": "Lin Yue", "current_state": "Committed"}]}
    save_json(str(project_root / "characters.json"), committed_characters)
    save_json(str(project_root / "timeline.json"), {"events": []})
    save_json(str(project_root / "foreshadow.json"), {"items": []})
    save_json(review_path, _review_payload(project_root, chapter_no, committed=True))
    save_json(suggestion_path, _suggestion_payload(chapter_no, committed=True))
    create_pending_snapshot(
        project_root=str(project_root),
        chapter_no=chapter_no,
        review_path=review_path,
        suggestion_path=suggestion_path,
        state_before=_state_before(),
    )
    monkeypatch.setattr(
        "core.longform.snapshot_service._delete_snapshot_file",
        lambda path: (_ for _ in ()).throw(PermissionError("snapshot delete blocked")),
    )

    with pytest.raises(Exception, match="stale snapshot cleanup"):
        handle_preflight_snapshot(str(project_root), chapter_no)

    assert Path(snapshot_path).exists()
    assert load_json(str(project_root / "characters.json")) == committed_characters
