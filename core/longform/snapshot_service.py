from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.longform.project_state_repository import (
    get_chapter_review_path,
    get_chapter_snapshot_path,
)
from core.project_service import (
    get_chapter_suggestion_path,
    get_project_file_paths,
)
from core.storage import load_json, save_json


SNAPSHOT_VERSION = 1
STATUS_PENDING = "pending"
STATUS_RESTORED = "restored"


def create_pending_snapshot(
    project_root: str,
    chapter_no: int,
    review_path: str,
    suggestion_path: str,
    state_before: dict[str, Any],
) -> dict[str, Any]:
    """Persist the canonical pre-commit snapshot for one chapter."""
    snapshot = {
        "version": SNAPSHOT_VERSION,
        "chapter_no": chapter_no,
        "created_at": _utc_now_iso(),
        "status": STATUS_PENDING,
        "review_path": review_path,
        "suggestion_path": suggestion_path,
        "state_before": deepcopy(state_before),
        "restored_at": None,
        "last_error": None,
    }
    save_json(get_chapter_snapshot_path(project_root, chapter_no), snapshot)
    return snapshot


def handle_preflight_snapshot(project_root: str, chapter_no: int) -> dict[str, Any] | None:
    """Resolve an unfinished or stale snapshot before a new commit attempt starts."""
    snapshot_path = get_chapter_snapshot_path(project_root, chapter_no)
    if not Path(snapshot_path).is_file():
        return None

    review_path, suggestion_path = _canonical_artifact_paths(project_root, chapter_no)
    review = _load_optional_artifact(review_path)
    suggestion = _load_optional_artifact(suggestion_path)

    if _artifact_is_committed(review) and _artifact_is_committed(suggestion):
        _cleanup_snapshot_or_raise(
            snapshot_path,
            f"Failed during stale snapshot cleanup for chapter {chapter_no}",
        )
        return {
            "status": "already_committed",
            "approved_suggestion": _resolve_committed_suggestion_payload(
                review=review,
                suggestion=suggestion,
                chapter_no=chapter_no,
            ),
        }

    recover_failed_commit_with_snapshot(
        project_root=project_root,
        chapter_no=chapter_no,
        failure_reason="preflight unresolved snapshot restore",
    )
    _cleanup_snapshot_or_raise(
        snapshot_path,
        f"Failed during preflight unresolved snapshot cleanup for chapter {chapter_no}",
    )
    return {"status": "restored"}


def recover_failed_commit_with_snapshot(
    project_root: str,
    chapter_no: int,
    failure_reason: str,
) -> dict[str, Any]:
    """Restore formal state and commit markers from the canonical snapshot."""
    snapshot_path = get_chapter_snapshot_path(project_root, chapter_no)
    snapshot = _load_snapshot(snapshot_path, chapter_no)
    restore_errors: list[str] = []
    restored_at = _utc_now_iso()

    restore_errors.extend(_restore_commit_markers(project_root, chapter_no))
    restore_errors.extend(_restore_formal_state(project_root, snapshot))

    snapshot_error = failure_reason
    if restore_errors:
        snapshot_error = f"{failure_reason} | restore failed: {'; '.join(restore_errors)}"

    try:
        save_json(
            snapshot_path,
            {
                **snapshot,
                "status": STATUS_RESTORED if not restore_errors else snapshot.get("status", STATUS_PENDING),
                "restored_at": restored_at if not restore_errors else snapshot.get("restored_at"),
                "last_error": snapshot_error,
            },
        )
    except Exception as exc:
        restore_errors.append(f"snapshot update failed: {exc}")

    if restore_errors:
        raise RuntimeError(
            f"{failure_reason} | restore failed: {'; '.join(restore_errors)}"
        )

    return load_json(snapshot_path)  # type: ignore[return-value]


def cleanup_snapshot_after_commit(project_root: str, chapter_no: int) -> None:
    """Delete the canonical snapshot after a fully successful commit."""
    snapshot_path = get_chapter_snapshot_path(project_root, chapter_no)
    if not Path(snapshot_path).is_file():
        return
    _cleanup_snapshot_or_raise(
        snapshot_path,
        f"Failed during snapshot cleanup for chapter {chapter_no}",
    )


def _load_snapshot(path: str, chapter_no: int) -> dict[str, Any]:
    data = load_json(path)
    if not isinstance(data, dict):
        raise ValueError("Snapshot file must contain a JSON object.")

    if data.get("version") != SNAPSHOT_VERSION:
        raise ValueError(f"Unsupported snapshot version: {data.get('version')}")

    if data.get("chapter_no") != chapter_no:
        raise ValueError(
            f"Snapshot chapter_no mismatch: expected {chapter_no}, got {data.get('chapter_no')}."
        )

    state_before = data.get("state_before")
    if not isinstance(state_before, dict):
        raise ValueError("Snapshot field 'state_before' must be a JSON object.")

    for key in ("characters", "timeline", "foreshadow"):
        if key not in state_before:
            raise ValueError(f"Snapshot state_before is missing required field: {key}")
        if not isinstance(state_before[key], dict):
            raise ValueError(f"Snapshot state_before.{key} must be a JSON object.")

    return data


def _restore_commit_markers(project_root: str, chapter_no: int) -> list[str]:
    errors: list[str] = []
    review_path, suggestion_path = _canonical_artifact_paths(project_root, chapter_no)

    if Path(review_path).is_file():
        try:
            review = load_json(review_path)
            if not isinstance(review, dict):
                raise ValueError("Review file must contain a JSON object.")
            save_json(
                review_path,
                {
                    **review,
                    "committed": False,
                    "committed_chapter_no": None,
                },
            )
        except Exception as exc:
            errors.append(f"review restore failed: {exc}")

    if Path(suggestion_path).is_file():
        try:
            suggestion = load_json(suggestion_path)
            if not isinstance(suggestion, dict):
                raise ValueError("Suggestion file must contain a JSON object.")
            restored_suggestion = dict(suggestion)
            restored_suggestion.pop("committed", None)
            restored_suggestion.pop("committed_chapter_no", None)
            save_json(suggestion_path, restored_suggestion)
        except Exception as exc:
            errors.append(f"suggestion restore failed: {exc}")

    return errors


def _restore_formal_state(project_root: str, snapshot: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    paths = get_project_file_paths(project_root)
    state_before = snapshot["state_before"]

    targets = (
        (paths["characters_json"], state_before["characters"], "characters restore failed"),
        (paths["timeline_json"], state_before["timeline"], "timeline restore failed"),
        (paths["foreshadow_json"], state_before["foreshadow"], "foreshadow restore failed"),
    )
    for path, payload, label in targets:
        try:
            save_json(path, deepcopy(payload))
        except Exception as exc:
            errors.append(f"{label}: {exc}")

    return errors


def _cleanup_snapshot_or_raise(snapshot_path: str, error_prefix: str) -> None:
    try:
        _delete_snapshot_file(snapshot_path)
    except Exception as exc:
        raise RuntimeError(f"{error_prefix}: {exc}") from exc


def _delete_snapshot_file(path: str) -> None:
    Path(path).unlink()


def _canonical_artifact_paths(project_root: str, chapter_no: int) -> tuple[str, str]:
    suggestion_path = get_chapter_suggestion_path(project_root, chapter_no)
    review_path = get_chapter_review_path(project_root, chapter_no)
    return review_path, suggestion_path


def _load_optional_artifact(path: str) -> dict[str, Any] | None:
    if not Path(path).is_file():
        return None
    data = load_json(path)
    if not isinstance(data, dict):
        raise ValueError(f"Artifact file must contain a JSON object: {path}")
    return data


def _artifact_is_committed(data: dict[str, Any] | None) -> bool:
    return isinstance(data, dict) and data.get("committed") is True


def _resolve_committed_suggestion_payload(
    review: dict[str, Any] | None,
    suggestion: dict[str, Any] | None,
    chapter_no: int,
) -> dict[str, Any]:
    if isinstance(review, dict):
        approved = review.get("approved_suggestion")
        if isinstance(approved, dict) and approved.get("chapter_no") == chapter_no:
            return approved

    if isinstance(suggestion, dict) and suggestion.get("chapter_no") == chapter_no:
        return suggestion

    raise ValueError(
        f"Failed to resolve committed suggestion payload for chapter {chapter_no}."
    )


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
