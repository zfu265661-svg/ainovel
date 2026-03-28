from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.longform.consistency_service import CONSISTENCY_CHECK_VERSION
from core.longform.project_state_repository import get_chapter_review_path
from core.project_service import get_chapter_suggestion_path
from core.storage import load_json, save_json


REVIEW_VERSION = 1
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
    "character_updates",
    "timeline_updates",
    "foreshadow_updates",
    "notes",
)
UPDATE_FIELDS: tuple[str, ...] = ("action", "target", "content")


def create_or_refresh_review(project_root: str, chapter_no: int) -> dict[str, Any]:
    """Create or refresh the canonical review artifact from the current disk suggestion."""
    suggestion_path = get_chapter_suggestion_path(project_root, chapter_no)
    review_path = get_chapter_review_path(project_root, chapter_no)
    suggestion = _load_suggestion_for_review(suggestion_path, chapter_no)
    created_at = _utc_now_iso()

    if Path(review_path).is_file():
        existing_review = _load_raw_review(review_path)
        if existing_review.get("committed") is True:
            raise ValueError(f"Review for chapter {chapter_no} has already been committed.")

    review = {
        "version": REVIEW_VERSION,
        "chapter_no": chapter_no,
        "created_at": created_at,
        "suggestion_path": suggestion_path,
        "approved_suggestion": suggestion,
        "committed": False,
        "committed_chapter_no": None,
    }
    save_json(review_path, review)
    return review


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

    _validate_updates("character_updates", suggestion["character_updates"])
    _validate_updates("timeline_updates", suggestion["timeline_updates"])
    _validate_updates("foreshadow_updates", suggestion["foreshadow_updates"])


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


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
