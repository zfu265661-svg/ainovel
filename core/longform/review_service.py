from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.longform.consistency_service import (
    CONSISTENCY_CHECK_VERSION,
    run_review_consistency_check,
)
from core.longform.project_state_repository import (
    get_chapter_review_path,
    get_longform_file_paths,
)
from core.longform.state_targets import get_required_suggestion_update_fields
from core.project_service import get_chapter_suggestion_path
from core.storage import load_json, save_json


REVIEW_VERSION = 1
STATUS_PENDING = "pending"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"
STATUS_COMMITTED = "committed"
REVIEW_STATUSES = (
    STATUS_PENDING,
    STATUS_APPROVED,
    STATUS_REJECTED,
    STATUS_COMMITTED,
)
REQUIRED_REVIEW_FIELDS: tuple[str, ...] = (
    "version",
    "chapter_no",
    "created_at",
    "suggestion_path",
    "approved_suggestion",
    "consistency_check",
    "committed",
    "committed_chapter_no",
)
REQUIRED_SUGGESTION_FIELDS: tuple[str, ...] = (
    "chapter_no",
    *get_required_suggestion_update_fields(),
    "notes",
)
UPDATE_FIELDS: tuple[str, ...] = ("action", "target", "content")
_REVIEW_FILE_SUFFIX = ".review.json"


def create_or_refresh_review(project_root: str, chapter_no: int) -> dict[str, Any]:
    """Create or refresh the canonical review artifact from the current disk suggestion."""
    suggestion_path = get_chapter_suggestion_path(project_root, chapter_no)
    review_path = get_chapter_review_path(project_root, chapter_no)
    suggestion = _load_suggestion_for_review(suggestion_path, chapter_no)
    created_at = _utc_now_iso()

    if Path(review_path).is_file():
        existing_review = _load_raw_review(review_path)
        existing_status = normalize_review_status(existing_review)
        if existing_status == STATUS_COMMITTED:
            raise ValueError(f"Review for chapter {chapter_no} has already been committed.")
        if existing_status != STATUS_PENDING:
            raise ValueError(
                f"Only pending review can be refreshed; current status is {existing_status}."
            )

    review = _with_review_control_defaults({
        "version": REVIEW_VERSION,
        "chapter_no": chapter_no,
        "created_at": created_at,
        "suggestion_path": suggestion_path,
        "approved_suggestion": suggestion,
        "committed": False,
        "committed_chapter_no": None,
    })
    save_json(review_path, review)
    return review


def prepare_review(project_root: str, chapter_no: int) -> dict[str, Any]:
    """Create or refresh a pending review and run deterministic checks only."""
    create_or_refresh_review(project_root, chapter_no)
    review = run_review_consistency_check(project_root, chapter_no)
    return load_review_for_display(project_root, chapter_no) | {
        "consistency_check": review["consistency_check"],
    }


def list_reviews(project_root: str) -> list[dict[str, Any]]:
    """List review artifacts with normalized status metadata."""
    reviews_dir = Path(get_longform_file_paths(project_root)["reviews_dir"])
    if not reviews_dir.is_dir():
        return []

    reviews: list[dict[str, Any]] = []
    for path in sorted(reviews_dir.glob(f"*{_REVIEW_FILE_SUFFIX}")):
        try:
            review = _load_raw_review(str(path))
            status = normalize_review_status(review)
            chapter_no = review.get("chapter_no")
            consistency_check = review.get("consistency_check")
            reviews.append(
                {
                    "chapter_no": chapter_no if isinstance(chapter_no, int) else None,
                    "status": status,
                    "has_consistency_check": isinstance(consistency_check, dict),
                    "committed": review.get("committed") is True,
                    "review_path": str(path),
                }
            )
        except Exception as exc:
            reviews.append(
                {
                    "chapter_no": _chapter_no_from_review_file_name(path.name),
                    "status": "invalid",
                    "has_consistency_check": False,
                    "committed": False,
                    "review_path": str(path),
                    "error": str(exc),
                }
            )

    return sorted(
        reviews,
        key=lambda item: (
            item["chapter_no"] is None,
            item["chapter_no"] if isinstance(item["chapter_no"], int) else 0,
            item["review_path"],
        ),
    )


def load_review_for_display(project_root: str, chapter_no: int) -> dict[str, Any]:
    """Load one review for read-only display with compatibility defaults."""
    review_path = get_chapter_review_path(project_root, chapter_no)
    review = _load_raw_review(review_path)
    status = normalize_review_status(review)
    approved_suggestion = review.get("approved_suggestion")
    suggestion_summary = (
        _summarize_suggestion(approved_suggestion)
        if isinstance(approved_suggestion, dict)
        else _empty_suggestion_summary()
    )

    return {
        "review_path": review_path,
        "chapter_no": review.get("chapter_no"),
        "status": status,
        "suggestion_path": review.get("suggestion_path"),
        "approved_suggestion_summary": suggestion_summary,
        "approved_suggestion": approved_suggestion if isinstance(approved_suggestion, dict) else {},
        "consistency_check": review.get("consistency_check") if isinstance(review.get("consistency_check"), dict) else {},
        "review_notes": _review_notes(review),
        "reject_reason": _string_field(review, "reject_reason"),
        "approved_at": _string_field(review, "approved_at"),
        "rejected_at": _string_field(review, "rejected_at"),
        "committed_at": _string_field(review, "committed_at"),
        "committed": review.get("committed") is True,
        "committed_chapter_no": review.get("committed_chapter_no"),
    }


def approve_review(project_root: str, chapter_no: int) -> dict[str, Any]:
    """Mark a pending review as approved without committing formal state."""
    review_path = get_chapter_review_path(project_root, chapter_no)
    review = _load_raw_review(review_path)
    status = normalize_review_status(review)
    _ensure_pending_transition(status, chapter_no, "approve")
    _assert_consistency_check_has_no_blockers(review)

    approved = {
        **_with_review_control_defaults(review),
        "status": STATUS_APPROVED,
        "approved_at": _utc_now_iso(),
        "rejected_at": "",
        "reject_reason": "",
    }
    save_json(review_path, approved)
    return load_review_for_display(project_root, chapter_no)


def reject_review(project_root: str, chapter_no: int, reason: str) -> dict[str, Any]:
    """Mark a pending review as rejected without committing formal state."""
    normalized_reason = str(reason).strip()
    if not normalized_reason:
        raise ValueError("Reject reason must be a non-empty string.")

    review_path = get_chapter_review_path(project_root, chapter_no)
    review = _load_raw_review(review_path)
    status = normalize_review_status(review)
    _ensure_pending_transition(status, chapter_no, "reject")

    rejected = {
        **_with_review_control_defaults(review),
        "status": STATUS_REJECTED,
        "reject_reason": normalized_reason,
        "rejected_at": _utc_now_iso(),
    }
    save_json(review_path, rejected)
    return load_review_for_display(project_root, chapter_no)


def assert_review_can_commit(project_root: str, chapter_no: int) -> dict[str, Any]:
    """Validate that a review is explicitly approved for manual commit."""
    review_path = get_chapter_review_path(project_root, chapter_no)
    if not Path(review_path).is_file():
        raise ValueError(f"Review for chapter {chapter_no} was not found.")

    review = _load_raw_review(review_path)
    status = normalize_review_status(review)
    if status == STATUS_PENDING:
        raise ValueError(f"Review for chapter {chapter_no} has not been approved.")
    if status == STATUS_REJECTED:
        raise ValueError(f"Review for chapter {chapter_no} has been rejected.")
    if status == STATUS_COMMITTED:
        raise ValueError(f"Review for chapter {chapter_no} has already been committed.")
    if status != STATUS_APPROVED:
        raise ValueError(f"Review for chapter {chapter_no} cannot be committed from status: {status}.")

    return review


def normalize_review_status(review: dict[str, Any]) -> str:
    """Return the effective review status while preserving legacy artifacts."""
    raw_status = review.get("status")
    if raw_status is not None:
        if not isinstance(raw_status, str) or raw_status not in REVIEW_STATUSES:
            raise ValueError(f"Unsupported review status: {raw_status}")
        if raw_status == STATUS_COMMITTED:
            return STATUS_COMMITTED

    if review.get("committed") is True:
        return STATUS_COMMITTED

    if isinstance(raw_status, str):
        return raw_status

    return STATUS_PENDING


def load_review_for_commit(project_root: str, chapter_no: int) -> dict[str, Any]:
    """Load and validate the canonical review artifact used as commit input."""
    review_path = get_chapter_review_path(project_root, chapter_no)
    suggestion_path = get_chapter_suggestion_path(project_root, chapter_no)
    review = _load_raw_review(review_path)
    _validate_review(review, chapter_no, suggestion_path)
    return review


def _load_raw_review(path: str) -> dict[str, Any]:
    data = load_json(path)
    if not isinstance(data, dict):
        raise ValueError("Review file must contain a JSON object.")
    return data


def _validate_review(
    review: dict[str, Any],
    chapter_no: int,
    suggestion_path: str,
) -> None:
    missing_fields = [field for field in REQUIRED_REVIEW_FIELDS if field not in review]
    if missing_fields:
        missing = ", ".join(missing_fields)
        raise ValueError(f"Review is missing required field(s): {missing}")

    if review["version"] != REVIEW_VERSION:
        raise ValueError(f"Unsupported review version: {review['version']}")

    if not isinstance(review["chapter_no"], int):
        raise ValueError("Review field 'chapter_no' must be an integer.")
    if review["chapter_no"] != chapter_no:
        raise ValueError(
            f"Review chapter_no mismatch: expected {chapter_no}, got {review['chapter_no']}."
        )

    created_at = review["created_at"]
    if not isinstance(created_at, str) or not created_at.strip():
        raise ValueError("Review field 'created_at' must be a non-empty string.")

    if review["suggestion_path"] != suggestion_path:
        raise ValueError(
            "Review suggestion_path mismatch: "
            f"expected {suggestion_path}, got {review['suggestion_path']}."
        )

    if not isinstance(review["committed"], bool):
        raise ValueError("Review field 'committed' must be a boolean.")
    if review["committed"] is True:
        raise ValueError(f"Review for chapter {chapter_no} has already been committed.")
    if normalize_review_status(review) == STATUS_REJECTED:
        raise ValueError(f"Review for chapter {chapter_no} has been rejected.")

    committed_chapter_no = review["committed_chapter_no"]
    if committed_chapter_no is not None and not isinstance(committed_chapter_no, int):
        raise ValueError("Review field 'committed_chapter_no' must be an integer or null.")

    approved_suggestion = review["approved_suggestion"]
    if not isinstance(approved_suggestion, dict):
        raise ValueError("Review field 'approved_suggestion' must be a JSON object.")

    _validate_suggestion_payload(approved_suggestion)

    if approved_suggestion["chapter_no"] != review["chapter_no"]:
        raise ValueError(
            "Review approved_suggestion.chapter_no mismatch: "
            f"expected {review['chapter_no']}, got {approved_suggestion['chapter_no']}."
        )

    _validate_consistency_check(review["consistency_check"])


def _load_suggestion_for_review(path: str, chapter_no: int) -> dict[str, Any]:
    data = load_json(path)
    if not isinstance(data, dict):
        raise ValueError("Suggestion file must contain a JSON object.")

    _validate_suggestion_payload(data)

    if data["chapter_no"] != chapter_no:
        raise ValueError(
            f"Suggestion chapter_no mismatch: expected {chapter_no}, got {data['chapter_no']}."
        )

    if data.get("committed") is True:
        raise ValueError(f"Suggestion for chapter {chapter_no} has already been committed.")

    return data


def _validate_suggestion_payload(suggestion: dict[str, Any]) -> None:
    missing_fields = [field for field in REQUIRED_SUGGESTION_FIELDS if field not in suggestion]
    if missing_fields:
        missing = ", ".join(missing_fields)
        raise ValueError(f"Suggestion is missing required field(s): {missing}")

    if not isinstance(suggestion["chapter_no"], int):
        raise ValueError("Suggestion field 'chapter_no' must be an integer.")

    for field_name in get_required_suggestion_update_fields():
        _validate_updates(field_name, suggestion[field_name])


def _validate_updates(field_name: str, updates: Any) -> None:
    if not isinstance(updates, list):
        raise ValueError(f"Suggestion field '{field_name}' must be a list.")

    for index, item in enumerate(updates, start=1):
        if not isinstance(item, dict):
            raise ValueError(
                f"Suggestion field '{field_name}' entry {index} must be a JSON object."
            )

        missing_fields = [field for field in UPDATE_FIELDS if field not in item]
        if missing_fields:
            missing = ", ".join(missing_fields)
            raise ValueError(
                f"Suggestion field '{field_name}' entry {index} is missing required field(s): {missing}"
            )


def _validate_consistency_check(consistency_check: Any) -> None:
    if not isinstance(consistency_check, dict):
        raise ValueError("Review field 'consistency_check' must be a JSON object.")

    missing_fields = [
        field
        for field in ("version", "checked_at", "blockers", "warnings")
        if field not in consistency_check
    ]
    if missing_fields:
        missing = ", ".join(missing_fields)
        raise ValueError(
            f"Review consistency_check is missing required field(s): {missing}"
        )

    if consistency_check["version"] != CONSISTENCY_CHECK_VERSION:
        raise ValueError(
            "Unsupported review consistency_check version: "
            f"{consistency_check['version']}"
        )

    checked_at = consistency_check["checked_at"]
    if not isinstance(checked_at, str) or not checked_at.strip():
        raise ValueError(
            "Review consistency_check field 'checked_at' must be a non-empty string."
        )

    blockers = consistency_check["blockers"]
    if not isinstance(blockers, list):
        raise ValueError("Review consistency_check field 'blockers' must be a list.")

    warnings = consistency_check["warnings"]
    if not isinstance(warnings, list):
        raise ValueError("Review consistency_check field 'warnings' must be a list.")

    if blockers:
        blocker_codes = []
        for blocker in blockers:
            if isinstance(blocker, dict):
                code = blocker.get("code")
                if isinstance(code, str) and code.strip():
                    blocker_codes.append(code.strip())
                    continue
            blocker_codes.append("unknown")
        raise ValueError(
            "Review consistency_check contains blocker(s): "
            + ", ".join(blocker_codes)
        )


def _with_review_control_defaults(review: dict[str, Any]) -> dict[str, Any]:
    return {
        **review,
        "status": normalize_review_status(review),
        "review_notes": _review_notes(review),
        "reject_reason": _string_field(review, "reject_reason"),
        "approved_at": _string_field(review, "approved_at"),
        "rejected_at": _string_field(review, "rejected_at"),
        "committed_at": _string_field(review, "committed_at"),
    }


def _review_notes(review: dict[str, Any]) -> list[Any]:
    notes = review.get("review_notes")
    return notes if isinstance(notes, list) else []


def _string_field(review: dict[str, Any], field_name: str) -> str:
    value = review.get(field_name)
    return value if isinstance(value, str) else ""


def _ensure_pending_transition(status: str, chapter_no: int, action: str) -> None:
    if status == STATUS_COMMITTED:
        raise ValueError(f"Review for chapter {chapter_no} has already been committed.")
    if status != STATUS_PENDING:
        raise ValueError(
            f"Only pending review can be {action}d; current status is {status}."
        )


def _assert_consistency_check_has_no_blockers(review: dict[str, Any]) -> None:
    consistency_check = review.get("consistency_check")
    if not isinstance(consistency_check, dict):
        raise ValueError("Review must have a consistency_check before approval.")

    blockers = consistency_check.get("blockers")
    if not isinstance(blockers, list):
        raise ValueError("Review consistency_check field 'blockers' must be a list.")

    if blockers:
        blocker_codes: list[str] = []
        for blocker in blockers:
            if isinstance(blocker, dict):
                code = blocker.get("code")
                if isinstance(code, str) and code.strip():
                    blocker_codes.append(code.strip())
                    continue
            blocker_codes.append("unknown")
        raise ValueError(
            "Review consistency_check contains blocker(s): "
            + ", ".join(blocker_codes)
        )


def _summarize_suggestion(suggestion: dict[str, Any]) -> dict[str, Any]:
    return {
        "chapter_no": suggestion.get("chapter_no"),
        "character_updates": len(suggestion.get("character_updates", []))
        if isinstance(suggestion.get("character_updates"), list)
        else 0,
        "timeline_updates": len(suggestion.get("timeline_updates", []))
        if isinstance(suggestion.get("timeline_updates"), list)
        else 0,
        "foreshadow_updates": len(suggestion.get("foreshadow_updates", []))
        if isinstance(suggestion.get("foreshadow_updates"), list)
        else 0,
        "notes": suggestion.get("notes") if isinstance(suggestion.get("notes"), str) else "",
    }


def _empty_suggestion_summary() -> dict[str, Any]:
    return {
        "chapter_no": None,
        "character_updates": 0,
        "timeline_updates": 0,
        "foreshadow_updates": 0,
        "notes": "",
    }


def _chapter_no_from_review_file_name(name: str) -> int | None:
    if not name.startswith("ch") or not name.endswith(_REVIEW_FILE_SUFFIX):
        return None
    raw_chapter_no = name[2 : -len(_REVIEW_FILE_SUFFIX)]
    return int(raw_chapter_no) if raw_chapter_no.isdigit() else None


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
