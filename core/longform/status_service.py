from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from core.longform.project_state_repository import (
    get_chapter_checkpoint_path,
    get_chapter_review_path,
    get_chapter_snapshot_path,
    get_longform_file_paths,
    load_project_loop_state,
)
from core.longform.state_targets import get_formal_state_targets
from core.project_service import get_chapter_suggestion_path, get_project_file_paths
from core.storage import load_json


_ARTIFACT_PATTERN = re.compile(
    r"^ch(?P<chapter>\d+)\.(?P<kind>checkpoint|review|snapshot|suggestion)\.json$"
)
_FAILURE_STAGE_PATTERNS: tuple[tuple[str, str], ...] = (
    ("Failed during preflight snapshot handling", "preflight_snapshot"),
    ("Failed during review creation", "review_creation"),
    ("Failed during review consistency check", "consistency_check"),
    ("Failed during review load", "review_load"),
    ("Failed during snapshot persistence", "formal_state_write"),
    ("Failed during characters state persistence", "formal_state_write"),
    ("Failed during character state persistence", "formal_state_write"),
    ("Failed during timeline state persistence", "formal_state_write"),
    ("Failed during foreshadow state persistence", "formal_state_write"),
    ("Failed during commit restore", "formal_state_write"),
    ("Failed during commit marker persistence", "marker_write"),
    ("Failed during snapshot cleanup", "snapshot_cleanup"),
    ("Failed during stale snapshot cleanup", "snapshot_cleanup"),
)
_FORMAL_STATE_FILE_KEYS: tuple[str, ...] = (
    "project_json",
    "chapters_json",
    "characters_json",
    "timeline_json",
    "foreshadow_json",
    "story_bible_json",
    "plot_threads_json",
    "locations_json",
    "organizations_json",
    "style_guide_json",
    "scenes_json",
)
_REQUIRED_FORMAL_STATE_FILE_KEYS: tuple[str, ...] = (
    "project_json",
    "chapters_json",
    "characters_json",
    "timeline_json",
    "foreshadow_json",
)
_ENHANCED_STATE_FILES: tuple[tuple[str, str, str | None], ...] = (
    ("story_bible", "story_bible_json", None),
    ("plot_threads", "plot_threads_json", "threads"),
    ("locations", "locations_json", "locations"),
    ("organizations", "organizations_json", "organizations"),
    ("style_guide", "style_guide_json", None),
    ("scenes", "scenes_json", "scenes"),
)


def build_project_status_report(project_root: str) -> dict[str, Any]:
    loop_state = load_project_loop_state(project_root)
    formal_state_health = _scan_formal_state_health(project_root)
    latest_checkpoint = _load_latest_checkpoint(project_root)
    committed_scan = _scan_last_successfully_committed(project_root)
    unresolved_snapshots, stale_snapshots = _scan_snapshot_health(project_root)

    loop_state_last_completed = int(loop_state["last_completed_chapter_no"])
    if committed_scan["exact"]:
        last_successfully_committed_chapter_no = committed_scan["chapter_no"]
        last_successfully_committed_source = "artifact_scan"
        commit_scan_status = "exact"
        commit_loop_drift = (
            last_successfully_committed_chapter_no != loop_state_last_completed
        )
    else:
        last_successfully_committed_chapter_no = loop_state_last_completed
        last_successfully_committed_source = "loop_state_fallback"
        commit_scan_status = "unknown"
        commit_loop_drift = True

    checkpoint_payload = latest_checkpoint["data"]
    last_attempted_chapter_no = latest_checkpoint["chapter_no"]
    if last_attempted_chapter_no is None:
        current_chapter_no = loop_state.get("current_chapter_no")
        last_attempted_chapter_no = (
            int(current_chapter_no) if isinstance(current_chapter_no, int) else None
        )

    artifact_focus_chapter_no = (
        last_attempted_chapter_no
        if isinstance(last_attempted_chapter_no, int)
        else (
            int(loop_state["current_chapter_no"])
            if isinstance(loop_state.get("current_chapter_no"), int)
            else int(loop_state["next_chapter_no"])
        )
    )
    chapter_diagnostics = build_chapter_diagnostic_report(
        project_root,
        artifact_focus_chapter_no,
        checkpoint_payload=checkpoint_payload
        if latest_checkpoint["chapter_no"] == artifact_focus_chapter_no
        else None,
    )

    checkpoint_error = latest_checkpoint["error"]
    last_error = _summarize_error(
        checkpoint_payload.get("error")
        if isinstance(checkpoint_payload, dict)
        else checkpoint_error
    )
    last_failure_stage = (
        chapter_diagnostics["failure_stage"]
        if isinstance(chapter_diagnostics["failure_stage"], str)
        else None
    )
    last_attempt_status = (
        checkpoint_payload.get("status")
        if isinstance(checkpoint_payload, dict)
        else ("unknown" if last_attempted_chapter_no is not None else None)
    )
    can_continue = _can_continue(formal_state_health)
    next_action = _derive_next_action(
        loop_state=loop_state,
        formal_state_health=formal_state_health,
        unresolved_snapshots=unresolved_snapshots,
        stale_snapshots=stale_snapshots,
        last_attempt_status=last_attempt_status,
    )

    return {
        "project_root": project_root,
        "workflow_status": loop_state["status"],
        "start_chapter_no": loop_state["start_chapter_no"],
        "target_chapter_count": loop_state["target_chapter_count"],
        "current_chapter_no": loop_state["current_chapter_no"],
        "next_chapter_no": loop_state["next_chapter_no"],
        "loop_state_last_completed_chapter_no": loop_state_last_completed,
        "last_successfully_committed_chapter_no": last_successfully_committed_chapter_no,
        "last_successfully_committed_source": last_successfully_committed_source,
        "commit_scan_status": commit_scan_status,
        "commit_loop_drift": commit_loop_drift,
        "last_attempted_chapter_no": last_attempted_chapter_no,
        "last_attempt_status": last_attempt_status,
        "last_failure_stage": last_failure_stage,
        "last_error": last_error,
        "formal_state_health": formal_state_health["health"],
        "formal_state_missing_files": formal_state_health["missing_files"],
        "formal_state_required_missing_files": formal_state_health["required_missing_files"],
        "formal_state_corrupt_files": formal_state_health["corrupt_files"],
        "formal_state_corrupt_file_errors": formal_state_health["corrupt_file_errors"],
        "narrative_state_machine": _build_narrative_state_machine_overview(
            project_root,
            formal_state_health,
        ),
        "can_continue": can_continue,
        "next_action": next_action,
        "unresolved_snapshot_exists": bool(unresolved_snapshots),
        "unresolved_snapshot_chapters": unresolved_snapshots,
        "stale_snapshot_exists": bool(stale_snapshots),
        "stale_snapshot_chapters": stale_snapshots,
        "artifact_focus_chapter_no": artifact_focus_chapter_no,
        "artifact_relation_status": chapter_diagnostics["artifact_relation_status"],
        "checkpoint_path": chapter_diagnostics["checkpoint_path"],
        "review_path": chapter_diagnostics["review_path"],
        "suggestion_path": chapter_diagnostics["suggestion_path"],
        "snapshot_path": chapter_diagnostics["snapshot_path"],
    }


def _build_narrative_state_machine_overview(
    project_root: str,
    formal_state_health: dict[str, Any],
) -> dict[str, Any]:
    project_paths = get_project_file_paths(project_root)
    longform_paths = get_longform_file_paths(project_root)
    missing_files = set(formal_state_health["missing_files"])
    corrupt_files = set(formal_state_health["corrupt_files"])

    enhanced_counts: dict[str, int] = {}
    for state_name, path_key, item_key in _ENHANCED_STATE_FILES:
        path = project_paths[path_key]
        enhanced_counts[state_name] = _count_state_items(path, item_key)

    checkpoints_dir = Path(longform_paths["checkpoints_dir"])
    reviews_dir = Path(longform_paths["reviews_dir"])
    snapshots_dir = Path(longform_paths["snapshots_dir"])
    suggestions_dir = Path(project_paths["suggestions_dir"])
    docs_dir = Path(project_paths["docs_dir"])

    return {
        "formal_state": {
            "targets": [target.name for target in get_formal_state_targets()],
            "health": formal_state_health["health"],
        },
        "enhanced_state": {
            "missing_optional": [
                Path(project_paths[path_key]).name
                for _state_name, path_key, _item_key in _ENHANCED_STATE_FILES
                if Path(project_paths[path_key]).name in missing_files
            ],
            "corrupt_optional": [
                Path(project_paths[path_key]).name
                for _state_name, path_key, _item_key in _ENHANCED_STATE_FILES
                if Path(project_paths[path_key]).name in corrupt_files
            ],
            "counts": enhanced_counts,
        },
        "process_artifacts": {
            "has_checkpoints": _directory_has_files(checkpoints_dir, "*.checkpoint.json"),
            "has_reviews": _directory_has_files(reviews_dir, "*.review.json"),
            "has_snapshots": _directory_has_files(snapshots_dir, "*.snapshot.json"),
            "has_suggestions": _directory_has_files(suggestions_dir, "*.suggestion.json"),
        },
        "derived_artifacts": {
            "has_chapter_summaries": _directory_has_files(docs_dir, "*.summary.md"),
            "chapter_summary_count": _count_files(docs_dir, "*.summary.md"),
            "context_audit_available": True,
        },
        "commit_boundary": {
            "enhanced_state_committed": False,
        },
    }


def _count_state_items(path: str, item_key: str | None) -> int:
    file_path = Path(path)
    if not file_path.is_file():
        return 0

    try:
        data = load_json(str(file_path))
    except Exception:
        return 0

    if not isinstance(data, dict):
        return 0

    if item_key is None:
        return len([key for key, value in data.items() if _has_content(value)])

    items = data.get(item_key)
    return len(items) if isinstance(items, list) else 0


def _has_content(value: Any) -> bool:
    if value in ("", None):
        return False
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def _directory_has_files(directory: Path, pattern: str) -> bool:
    return _count_files(directory, pattern) > 0


def _count_files(directory: Path, pattern: str) -> int:
    if not directory.is_dir():
        return 0
    return sum(1 for _path in directory.glob(pattern))


def _scan_formal_state_health(project_root: str) -> dict[str, Any]:
    paths = get_project_file_paths(project_root)
    missing_files: list[str] = []
    corrupt_files: list[str] = []
    corrupt_file_errors: dict[str, str] = {}
    required_missing_files: list[str] = []

    for key in _FORMAL_STATE_FILE_KEYS:
        path = Path(paths[key])
        if not path.is_file():
            missing_files.append(path.name)
            if key in _REQUIRED_FORMAL_STATE_FILE_KEYS:
                required_missing_files.append(path.name)
            continue

        try:
            data = load_json(str(path))
        except Exception as exc:
            corrupt_files.append(path.name)
            corrupt_file_errors[path.name] = str(exc)
            continue

        if not isinstance(data, dict):
            corrupt_files.append(path.name)
            corrupt_file_errors[path.name] = (
                f"Formal state file must contain a JSON object: {path}"
            )

    if corrupt_files:
        health = "corrupt"
    elif required_missing_files:
        health = "missing_required"
    elif missing_files:
        health = "missing_optional"
    else:
        health = "healthy"

    return {
        "health": health,
        "missing_files": missing_files,
        "required_missing_files": required_missing_files,
        "corrupt_files": corrupt_files,
        "corrupt_file_errors": corrupt_file_errors,
    }


def _can_continue(formal_state_health: dict[str, Any]) -> bool:
    return (
        not formal_state_health["required_missing_files"]
        and not formal_state_health["corrupt_files"]
    )


def _derive_next_action(
    loop_state: dict[str, Any],
    formal_state_health: dict[str, Any],
    unresolved_snapshots: list[int],
    stale_snapshots: list[int],
    last_attempt_status: Any,
) -> str:
    corrupt_files = formal_state_health["corrupt_files"]
    if corrupt_files:
        return f"inspect_formal_state:{corrupt_files[0]}"

    required_missing_files = formal_state_health["required_missing_files"]
    if required_missing_files:
        return f"restore_required_state:{required_missing_files[0]}"

    if unresolved_snapshots:
        return f"rerun_commit_or_loop_to_restore_snapshot:chapter_{unresolved_snapshots[0]}"

    if stale_snapshots:
        return f"rerun_commit_or_loop_to_cleanup_snapshot:chapter_{stale_snapshots[0]}"

    if last_attempt_status == "failed":
        return "inspect_checkpoint_then_rerun"

    if loop_state["status"] == "completed":
        return "export_or_inspect_project"

    return f"continue_from_chapter:{loop_state['next_chapter_no']}"


def build_chapter_diagnostic_report(
    project_root: str,
    chapter_no: int,
    checkpoint_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    checkpoint_path = get_chapter_checkpoint_path(project_root, chapter_no)
    review_path = get_chapter_review_path(project_root, chapter_no)
    suggestion_path = get_chapter_suggestion_path(project_root, chapter_no)
    snapshot_path = get_chapter_snapshot_path(project_root, chapter_no)

    checkpoint_state = (
        _state_from_payload(checkpoint_payload)
        if isinstance(checkpoint_payload, dict)
        else _safe_load_artifact(checkpoint_path)
    )
    review_state = _safe_load_artifact(review_path)
    suggestion_state = _safe_load_artifact(suggestion_path)
    snapshot_state = _safe_load_artifact(snapshot_path)

    artifact_relation_status = _classify_artifact_relation(
        chapter_no=chapter_no,
        checkpoint_path=checkpoint_path,
        review_path=review_path,
        suggestion_path=suggestion_path,
        snapshot_path=snapshot_path,
        checkpoint_state=checkpoint_state,
        review_state=review_state,
        suggestion_state=suggestion_state,
        snapshot_state=snapshot_state,
    )

    failure_stage = None
    if isinstance(checkpoint_state["data"], dict):
        checkpoint_data = checkpoint_state["data"]
        raw_stage = checkpoint_data.get("failure_stage")
        if isinstance(raw_stage, str) and raw_stage.strip():
            failure_stage = raw_stage.strip()
        else:
            failure_stage = derive_failure_stage(
                checkpoint_data.get("error")
                if isinstance(checkpoint_data.get("error"), str)
                else None
            )

    return {
        "chapter_no": chapter_no,
        "artifact_relation_status": artifact_relation_status,
        "checkpoint_path": checkpoint_path,
        "review_path": review_path,
        "suggestion_path": suggestion_path,
        "snapshot_path": snapshot_path,
        "failure_stage": failure_stage,
    }


def derive_failure_stage(error_message: str | None, default_stage: str | None = None) -> str | None:
    if not isinstance(error_message, str) or not error_message.strip():
        return default_stage

    normalized_error = error_message.strip()
    for pattern, stage in _FAILURE_STAGE_PATTERNS:
        if pattern in normalized_error:
            return stage

    return default_stage


def _load_latest_checkpoint(project_root: str) -> dict[str, Any]:
    checkpoints_dir = Path(get_longform_file_paths(project_root)["checkpoints_dir"])
    highest_chapter = None
    highest_path: Path | None = None

    if checkpoints_dir.is_dir():
        for path in checkpoints_dir.glob("*.checkpoint.json"):
            chapter_no = _extract_chapter_no_from_name(path.name, "checkpoint")
            if chapter_no is None:
                continue
            if highest_chapter is None or chapter_no > highest_chapter:
                highest_chapter = chapter_no
                highest_path = path

    if highest_chapter is None or highest_path is None:
        return {"chapter_no": None, "path": None, "data": None, "error": None}

    state = _safe_load_artifact(str(highest_path))
    return {
        "chapter_no": highest_chapter,
        "path": str(highest_path),
        "data": state["data"],
        "error": state["error"],
    }


def _scan_last_successfully_committed(project_root: str) -> dict[str, Any]:
    paths = get_longform_file_paths(project_root)
    reviews_dir = Path(paths["reviews_dir"])
    suggestions_dir = Path(get_longform_file_paths(project_root)["project_root"]) / "suggestions"
    chapters = sorted(
        set(_collect_artifact_chapters(reviews_dir, "review"))
        | set(_collect_artifact_chapters(suggestions_dir, "suggestion"))
    )

    highest_committed = 0
    for chapter_no in chapters:
        review_state = _safe_load_artifact(get_chapter_review_path(project_root, chapter_no))
        suggestion_state = _safe_load_artifact(get_chapter_suggestion_path(project_root, chapter_no))

        if _state_requires_unknown_for_commit_scan(review_state, "review"):
            return {"exact": False, "chapter_no": None}
        if _state_requires_unknown_for_commit_scan(suggestion_state, "suggestion"):
            return {"exact": False, "chapter_no": None}

        review_committed = _artifact_committed(review_state["data"])
        suggestion_committed = _artifact_committed(suggestion_state["data"])
        if review_committed and suggestion_committed:
            highest_committed = chapter_no

    return {"exact": True, "chapter_no": highest_committed}


def _scan_snapshot_health(project_root: str) -> tuple[list[int], list[int]]:
    snapshots_dir = Path(get_longform_file_paths(project_root)["snapshots_dir"])
    unresolved: list[int] = []
    stale: list[int] = []

    if not snapshots_dir.is_dir():
        return unresolved, stale

    for path in sorted(snapshots_dir.glob("*.snapshot.json")):
        chapter_no = _extract_chapter_no_from_name(path.name, "snapshot")
        if chapter_no is None:
            continue

        snapshot_state = _safe_load_artifact(str(path))
        if snapshot_state["error"] is not None or not isinstance(snapshot_state["data"], dict):
            unresolved.append(chapter_no)
            continue

        review_state = _safe_load_artifact(get_chapter_review_path(project_root, chapter_no))
        suggestion_state = _safe_load_artifact(get_chapter_suggestion_path(project_root, chapter_no))
        if _artifact_committed(review_state["data"]) and _artifact_committed(suggestion_state["data"]):
            stale.append(chapter_no)
        else:
            unresolved.append(chapter_no)

    return unresolved, stale


def _collect_artifact_chapters(directory: Path, kind: str) -> list[int]:
    if not directory.is_dir():
        return []

    chapters: list[int] = []
    for path in directory.glob(f"*.{kind}.json"):
        chapter_no = _extract_chapter_no_from_name(path.name, kind)
        if chapter_no is not None:
            chapters.append(chapter_no)
    return chapters


def _extract_chapter_no_from_name(name: str, kind: str) -> int | None:
    matched = _ARTIFACT_PATTERN.match(name)
    if matched is None or matched.group("kind") != kind:
        return None
    return int(matched.group("chapter"))


def _safe_load_artifact(path: str) -> dict[str, Any]:
    file_path = Path(path)
    if not file_path.is_file():
        return {
            "path": path,
            "exists": False,
            "data": None,
            "error": None,
        }

    try:
        data = load_json(path)
    except Exception as exc:
        return {
            "path": path,
            "exists": True,
            "data": None,
            "error": str(exc),
        }

    if not isinstance(data, dict):
        return {
            "path": path,
            "exists": True,
            "data": None,
            "error": f"Artifact file must contain a JSON object: {path}",
        }

    return {
        "path": path,
        "exists": True,
        "data": data,
        "error": None,
    }


def _state_from_payload(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "path": None,
        "exists": True,
        "data": data,
        "error": None,
    }


def _state_requires_unknown_for_commit_scan(state: dict[str, Any], kind: str) -> bool:
    if state["error"] is not None:
        return True
    if not state["exists"]:
        return False
    data = state["data"]
    if not isinstance(data, dict):
        return True
    if not isinstance(data.get("chapter_no"), int):
        return True
    if kind == "review":
        suggestion_path = data.get("suggestion_path")
        if not isinstance(suggestion_path, str) or not suggestion_path.strip():
            return True
    return False


def _classify_artifact_relation(
    chapter_no: int,
    checkpoint_path: str,
    review_path: str,
    suggestion_path: str,
    snapshot_path: str,
    checkpoint_state: dict[str, Any],
    review_state: dict[str, Any],
    suggestion_state: dict[str, Any],
    snapshot_state: dict[str, Any],
) -> str:
    states = {
        "checkpoint": checkpoint_state,
        "review": review_state,
        "suggestion": suggestion_state,
        "snapshot": snapshot_state,
    }
    if _has_unknown_artifact_state(states, review_path, suggestion_path):
        return "unknown"

    if _has_mismatched_artifacts(
        chapter_no=chapter_no,
        checkpoint_path=checkpoint_path,
        review_path=review_path,
        suggestion_path=suggestion_path,
        snapshot_path=snapshot_path,
        checkpoint_state=checkpoint_state,
        review_state=review_state,
        suggestion_state=suggestion_state,
        snapshot_state=snapshot_state,
    ):
        return "mismatched"

    if not all(bool(state["exists"]) for state in states.values()):
        return "partial"

    return "aligned"


def _has_unknown_artifact_state(
    states: dict[str, dict[str, Any]],
    review_path: str,
    suggestion_path: str,
) -> bool:
    for kind, state in states.items():
        if state["error"] is not None:
            return True
        if not state["exists"]:
            continue
        data = state["data"]
        if not isinstance(data, dict):
            return True
        if not isinstance(data.get("chapter_no"), int):
            return True
        if kind == "checkpoint":
            if not isinstance(data.get("artifacts"), dict):
                return True
        if kind == "review":
            if data.get("suggestion_path") != suggestion_path:
                continue
            committed = data.get("committed")
            if not isinstance(committed, bool):
                return True
        if kind == "suggestion":
            committed = data.get("committed")
            if committed is not None and not isinstance(committed, bool):
                return True
        if kind == "snapshot":
            if not isinstance(data.get("review_path"), str):
                return True
            if not isinstance(data.get("suggestion_path"), str):
                return True
    return False


def _has_mismatched_artifacts(
    chapter_no: int,
    checkpoint_path: str,
    review_path: str,
    suggestion_path: str,
    snapshot_path: str,
    checkpoint_state: dict[str, Any],
    review_state: dict[str, Any],
    suggestion_state: dict[str, Any],
    snapshot_state: dict[str, Any],
) -> bool:
    if checkpoint_state["exists"]:
        checkpoint_data = checkpoint_state["data"]
        if isinstance(checkpoint_data, dict):
            if checkpoint_data.get("chapter_no") != chapter_no:
                return True
            artifacts = checkpoint_data.get("artifacts")
            if isinstance(artifacts, dict):
                for key, expected in (
                    ("review_path", review_path),
                    ("suggestion_path", suggestion_path),
                    ("snapshot_path", snapshot_path),
                    ("checkpoint_path", checkpoint_path),
                ):
                    actual = artifacts.get(key)
                    if actual is not None and actual != expected:
                        return True

    if review_state["exists"]:
        review_data = review_state["data"]
        if isinstance(review_data, dict):
            if review_data.get("chapter_no") != chapter_no:
                return True
            if review_data.get("suggestion_path") != suggestion_path:
                return True

    if suggestion_state["exists"]:
        suggestion_data = suggestion_state["data"]
        if isinstance(suggestion_data, dict) and suggestion_data.get("chapter_no") != chapter_no:
            return True

    if snapshot_state["exists"]:
        snapshot_data = snapshot_state["data"]
        if isinstance(snapshot_data, dict):
            if snapshot_data.get("chapter_no") != chapter_no:
                return True
            if snapshot_data.get("review_path") != review_path:
                return True
            if snapshot_data.get("suggestion_path") != suggestion_path:
                return True

    if review_state["exists"] and suggestion_state["exists"]:
        review_committed = _artifact_committed(review_state["data"])
        suggestion_committed = _artifact_committed(suggestion_state["data"])
        if review_committed != suggestion_committed:
            return True

    return False


def _artifact_committed(data: Any) -> bool:
    return isinstance(data, dict) and data.get("committed") is True


def _summarize_error(error: Any) -> str | None:
    if not isinstance(error, str):
        return None
    line = error.strip().splitlines()[0] if error.strip() else ""
    return line or None
