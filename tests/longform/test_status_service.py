from __future__ import annotations

from pathlib import Path

from core.longform.project_state_repository import (
    get_chapter_checkpoint_path,
    get_chapter_review_path,
    get_chapter_snapshot_path,
    initialize_loop_state,
    save_project_loop_state,
)
from core.longform.status_service import (
    build_chapter_diagnostic_report,
    build_project_status_report,
)
from core.project_service import create_project_structure, get_chapter_suggestion_path
from core.storage import save_json, save_text


def test_build_project_status_report_scans_committed_artifacts_and_latest_failure(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "status-project"
    create_project_structure(
        str(project_root),
        title="Status Novel",
        topic="xianxia",
        style="cold",
        target="serial",
    )
    initial_state = initialize_loop_state(str(project_root), target_chapter_count=5)
    save_project_loop_state(
        str(project_root),
        {
            **initial_state,
            "status": "failed",
            "last_completed_chapter_no": 1,
            "next_chapter_no": 2,
            "current_chapter_no": 2,
        },
    )

    _save_committed_pair(str(project_root), 1)
    _save_uncommitted_pair(str(project_root), 2)
    save_json(
        get_chapter_checkpoint_path(str(project_root), 2),
        {
            "chapter_no": 2,
            "status": "failed",
            "failure_stage": "consistency_check",
            "artifacts": {
                "draft_path": str(project_root / "docs" / "ch002.draft.md"),
                "rewrite_path": str(project_root / "docs" / "ch002.rewrite.md"),
                "summary_path": str(project_root / "docs" / "ch002.summary.md"),
                "suggestion_path": get_chapter_suggestion_path(str(project_root), 2),
                "review_path": get_chapter_review_path(str(project_root), 2),
            },
            "suggestion_committed": False,
            "error": "Failed during review consistency check: blocked",
            "loop_state": {
                "status": "failed",
                "next_chapter_no": 2,
                "last_completed_chapter_no": 1,
                "current_chapter_no": 2,
            },
        },
    )

    report = build_project_status_report(str(project_root))

    assert report["workflow_status"] == "failed"
    assert report["last_successfully_committed_chapter_no"] == 1
    assert report["last_successfully_committed_source"] == "artifact_scan"
    assert report["commit_scan_status"] == "exact"
    assert report["commit_loop_drift"] is False
    assert report["last_attempted_chapter_no"] == 2
    assert report["last_attempt_status"] == "failed"
    assert report["last_failure_stage"] == "consistency_check"
    assert report["formal_state_health"] == "healthy"
    assert report["formal_state_missing_files"] == []
    assert report["formal_state_required_missing_files"] == []
    assert report["formal_state_corrupt_files"] == []
    assert report["formal_state_corrupt_file_errors"] == {}
    assert report["narrative_state_machine"]["formal_state"] == {
        "targets": ["characters", "timeline", "foreshadow"],
        "health": "healthy",
    }
    assert report["narrative_state_machine"]["enhanced_state"]["counts"]["plot_threads"] == 0
    assert report["narrative_state_machine"]["commit_boundary"] == {
        "enhanced_state_committed": False
    }
    assert report["can_continue"] is True
    assert report["next_action"] == "inspect_checkpoint_then_rerun"
    assert report["artifact_focus_chapter_no"] == 2
    assert report["artifact_relation_status"] == "partial"
    assert report["checkpoint_path"] == get_chapter_checkpoint_path(str(project_root), 2)
    assert report["review_path"] == get_chapter_review_path(str(project_root), 2)
    assert report["suggestion_path"] == get_chapter_suggestion_path(str(project_root), 2)
    assert report["snapshot_path"] == get_chapter_snapshot_path(str(project_root), 2)
    assert report["unresolved_snapshot_exists"] is False
    assert report["stale_snapshot_exists"] is False


def test_build_project_status_report_falls_back_to_loop_state_when_commit_scan_is_unknown(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "status-project"
    create_project_structure(
        str(project_root),
        title="Status Novel",
        topic="xianxia",
        style="cold",
        target="serial",
    )
    initial_state = initialize_loop_state(str(project_root), target_chapter_count=5)
    save_project_loop_state(
        str(project_root),
        {
            **initial_state,
            "status": "ready",
            "last_completed_chapter_no": 2,
            "next_chapter_no": 3,
            "current_chapter_no": None,
        },
    )

    _save_committed_pair(str(project_root), 1)
    save_text(get_chapter_review_path(str(project_root), 2), "{not valid json")

    report = build_project_status_report(str(project_root))

    assert report["last_successfully_committed_chapter_no"] == 2
    assert report["last_successfully_committed_source"] == "loop_state_fallback"
    assert report["commit_scan_status"] == "unknown"
    assert report["commit_loop_drift"] is True
    assert "scan is unknown" in report["commit_loop_drift_explanation"]


def test_build_project_status_report_explains_expected_manual_commit_drift(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "manual-status-project"
    create_project_structure(
        str(project_root),
        title="Manual Status Novel",
        topic="xianxia",
        style="cold",
        target="serial",
    )
    initialize_loop_state(str(project_root), target_chapter_count=5)
    _save_committed_pair(str(project_root), 1)

    report = build_project_status_report(str(project_root))

    assert report["last_successfully_committed_chapter_no"] == 1
    assert report["last_successfully_committed_source"] == "artifact_scan"
    assert report["loop_state_last_completed_chapter_no"] == 0
    assert report["commit_loop_drift"] is True
    assert "manual commit-approved" in report["commit_loop_drift_explanation"]
    assert "does not advance loop_state" in report["manual_commit_note"]
    assert report["artifact_relation_status"] == "partial"
    assert "informational" in report["artifact_relation_explanation"]
    assert report["can_continue"] is True
    assert report["next_action"] == "continue_from_chapter:1"


def test_build_project_status_report_reports_missing_optional_agent_state(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "status-project"
    create_project_structure(
        str(project_root),
        title="Status Novel",
        topic="xianxia",
        style="cold",
        target="serial",
    )
    initialize_loop_state(str(project_root), target_chapter_count=5)
    (project_root / "story_bible.json").unlink()

    report = build_project_status_report(str(project_root))

    assert report["formal_state_health"] == "missing_optional"
    assert report["formal_state_missing_files"] == ["story_bible.json"]
    assert report["formal_state_required_missing_files"] == []
    assert report["formal_state_corrupt_files"] == []
    assert report["formal_state_corrupt_file_errors"] == {}
    assert report["narrative_state_machine"]["enhanced_state"]["missing_optional"] == [
        "story_bible.json"
    ]
    assert report["narrative_state_machine"]["commit_boundary"]["enhanced_state_committed"] is False
    assert report["can_continue"] is True
    assert report["next_action"] == "continue_from_chapter:1"


def test_build_project_status_report_blocks_on_corrupt_agent_state(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "status-project"
    create_project_structure(
        str(project_root),
        title="Status Novel",
        topic="xianxia",
        style="cold",
        target="serial",
    )
    initialize_loop_state(str(project_root), target_chapter_count=5)
    save_text(str(project_root / "locations.json"), "{broken json")

    report = build_project_status_report(str(project_root))

    assert report["formal_state_health"] == "corrupt"
    assert report["formal_state_corrupt_files"] == ["locations.json"]
    assert "Failed to parse JSON file" in report["formal_state_corrupt_file_errors"]["locations.json"]
    assert report["narrative_state_machine"]["enhanced_state"]["corrupt_optional"] == [
        "locations.json"
    ]
    assert report["narrative_state_machine"]["enhanced_state"]["counts"]["locations"] == 0
    assert report["can_continue"] is False
    assert report["next_action"] == "inspect_formal_state:locations.json"


def test_build_project_status_report_allows_legacy_project_without_phase3_state(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "legacy-status-project"
    project_root.mkdir()
    save_json(
        str(project_root / "project.json"),
        {
            "project_id": "legacy-status-project",
            "title": "Legacy Novel",
            "topic": "xianxia",
            "style": "cold",
            "target": "serial",
            "current_chapter_no": 1,
            "status": "created",
        },
    )
    save_json(str(project_root / "chapters.json"), {"chapters": []})
    save_json(str(project_root / "characters.json"), {"characters": []})
    save_json(str(project_root / "timeline.json"), {"events": []})
    save_json(str(project_root / "foreshadow.json"), {"items": []})
    initialize_loop_state(str(project_root), target_chapter_count=5)

    report = build_project_status_report(str(project_root))

    assert report["formal_state_health"] == "missing_optional"
    assert report["formal_state_required_missing_files"] == []
    assert report["formal_state_corrupt_files"] == []
    assert report["can_continue"] is True
    assert report["next_action"] == "continue_from_chapter:1"
    assert report["formal_state_missing_files"] == [
        "story_bible.json",
        "plot_threads.json",
        "locations.json",
        "organizations.json",
        "style_guide.json",
        "scenes.json",
    ]
    assert report["narrative_state_machine"]["enhanced_state"]["missing_optional"] == [
        "story_bible.json",
        "plot_threads.json",
        "locations.json",
        "organizations.json",
        "style_guide.json",
        "scenes.json",
    ]
    assert report["narrative_state_machine"]["enhanced_state"]["counts"] == {
        "story_bible": 0,
        "plot_threads": 0,
        "locations": 0,
        "organizations": 0,
        "style_guide": 0,
        "scenes": 0,
    }


def test_build_project_status_report_detects_unresolved_and_stale_snapshots(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "status-project"
    create_project_structure(
        str(project_root),
        title="Status Novel",
        topic="xianxia",
        style="cold",
        target="serial",
    )
    initialize_loop_state(str(project_root), target_chapter_count=5)

    _save_committed_pair(str(project_root), 1)
    _save_uncommitted_pair(str(project_root), 2)
    save_json(
        get_chapter_snapshot_path(str(project_root), 1),
        _snapshot_payload(str(project_root), 1),
    )
    save_json(
        get_chapter_snapshot_path(str(project_root), 2),
        _snapshot_payload(str(project_root), 2),
    )

    report = build_project_status_report(str(project_root))

    assert report["stale_snapshot_exists"] is True
    assert report["stale_snapshot_chapters"] == [1]
    assert report["unresolved_snapshot_exists"] is True
    assert report["unresolved_snapshot_chapters"] == [2]


def test_build_chapter_diagnostic_report_classifies_aligned_partial_mismatched_and_unknown(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "status-project"
    create_project_structure(
        str(project_root),
        title="Status Novel",
        topic="xianxia",
        style="cold",
        target="serial",
    )

    _save_uncommitted_pair(str(project_root), 1)
    save_json(
        get_chapter_checkpoint_path(str(project_root), 1),
        _checkpoint_payload(str(project_root), 1, include_snapshot=True),
    )
    save_json(
        get_chapter_snapshot_path(str(project_root), 1),
        _snapshot_payload(str(project_root), 1),
    )

    _save_uncommitted_pair(str(project_root), 2)

    _save_uncommitted_pair(str(project_root), 3)
    save_json(
        get_chapter_suggestion_path(str(project_root), 3),
        {
            "chapter_no": 3,
            "character_updates": [],
            "timeline_updates": [],
            "foreshadow_updates": [],
            "notes": "Suggestion only.",
            "committed": True,
            "committed_chapter_no": 3,
        },
    )

    _save_uncommitted_pair(str(project_root), 4)
    save_text(get_chapter_review_path(str(project_root), 4), "{broken json")

    assert build_chapter_diagnostic_report(str(project_root), 1)["artifact_relation_status"] == "aligned"
    assert build_chapter_diagnostic_report(str(project_root), 2)["artifact_relation_status"] == "partial"
    assert build_chapter_diagnostic_report(str(project_root), 3)["artifact_relation_status"] == "mismatched"
    assert build_chapter_diagnostic_report(str(project_root), 4)["artifact_relation_status"] == "unknown"


def _checkpoint_payload(
    project_root: str,
    chapter_no: int,
    include_snapshot: bool = False,
) -> dict[str, object]:
    artifacts: dict[str, object] = {
        "suggestion_path": get_chapter_suggestion_path(project_root, chapter_no),
        "review_path": get_chapter_review_path(project_root, chapter_no),
    }
    if include_snapshot:
        artifacts["snapshot_path"] = get_chapter_snapshot_path(project_root, chapter_no)

    return {
        "chapter_no": chapter_no,
        "status": "failed",
        "failure_stage": "review_load",
        "artifacts": artifacts,
        "suggestion_committed": False,
        "error": "Failed during review load: broken review",
        "loop_state": {
            "status": "failed",
            "next_chapter_no": chapter_no,
            "last_completed_chapter_no": chapter_no - 1,
            "current_chapter_no": chapter_no,
        },
    }


def _save_committed_pair(project_root: str, chapter_no: int) -> None:
    save_json(
        get_chapter_suggestion_path(project_root, chapter_no),
        {
            "chapter_no": chapter_no,
            "character_updates": [],
            "timeline_updates": [],
            "foreshadow_updates": [],
            "notes": "Suggestion only.",
            "committed": True,
            "committed_chapter_no": chapter_no,
        },
    )
    save_json(
        get_chapter_review_path(project_root, chapter_no),
        _review_payload(project_root, chapter_no, committed=True),
    )


def _save_uncommitted_pair(project_root: str, chapter_no: int) -> None:
    save_json(
        get_chapter_suggestion_path(project_root, chapter_no),
        {
            "chapter_no": chapter_no,
            "character_updates": [],
            "timeline_updates": [],
            "foreshadow_updates": [],
            "notes": "Suggestion only.",
        },
    )
    save_json(
        get_chapter_review_path(project_root, chapter_no),
        _review_payload(project_root, chapter_no, committed=False),
    )


def _review_payload(project_root: str, chapter_no: int, committed: bool) -> dict[str, object]:
    return {
        "version": 1,
        "chapter_no": chapter_no,
        "created_at": "2026-03-28T12:00:00Z",
        "suggestion_path": get_chapter_suggestion_path(project_root, chapter_no),
        "approved_suggestion": {
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
    }


def _snapshot_payload(project_root: str, chapter_no: int) -> dict[str, object]:
    return {
        "version": 1,
        "chapter_no": chapter_no,
        "created_at": "2026-03-28T12:02:00Z",
        "status": "pending",
        "review_path": get_chapter_review_path(project_root, chapter_no),
        "suggestion_path": get_chapter_suggestion_path(project_root, chapter_no),
        "state_before": {
            "characters": {"characters": []},
            "timeline": {"events": []},
            "foreshadow": {"items": []},
        },
        "restored_at": None,
        "last_error": None,
    }
