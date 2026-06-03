from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.longform.project_state_repository import get_chapter_review_path
from core.longform.state_targets import get_formal_state_targets
from core.project_service import get_chapter_summary_path, get_project_file_paths
from core.storage import load_json, save_json


CONSISTENCY_CHECK_VERSION = 1


def run_review_consistency_check(project_root: str, chapter_no: int) -> dict[str, Any]:
    """Run deterministic checks against the canonical review and persist the result."""
    review_path = get_chapter_review_path(project_root, chapter_no)
    review = _load_review(review_path)

    if review.get("committed") is True:
        return review

    approved_suggestion = review.get("approved_suggestion")
    if not isinstance(approved_suggestion, dict):
        raise ValueError("Review field 'approved_suggestion' must be a JSON object.")

    review_chapter_no = review.get("chapter_no")
    effective_chapter_no = review_chapter_no if isinstance(review_chapter_no, int) else chapter_no
    consistency_check = _build_consistency_check(
        project_root=project_root,
        chapter_no=effective_chapter_no,
        approved_suggestion=approved_suggestion,
    )

    updated_review = {
        **review,
        "consistency_check": consistency_check,
    }
    save_json(review_path, updated_review)
    return updated_review


def _build_consistency_check(
    project_root: str,
    chapter_no: int,
    approved_suggestion: dict[str, Any],
) -> dict[str, Any]:
    blockers: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    _append_blank_update_field_blockers(blockers, approved_suggestion)
    _append_timeline_duplicate_blockers(
        blockers=blockers,
        chapter_no=chapter_no,
        timeline_updates=_get_update_list(approved_suggestion, "timeline_updates"),
        existing_keys=_load_existing_timeline_keys(project_root),
    )
    _append_previous_summary_warning(warnings, project_root, chapter_no)
    for target in get_formal_state_targets():
        if target.duplicate_warning_code is None:
            continue
        _append_duplicate_target_warning(
            warnings=warnings,
            updates=_get_update_list(approved_suggestion, target.update_field),
            field_name=target.update_field,
            code=target.duplicate_warning_code,
        )

    return {
        "version": CONSISTENCY_CHECK_VERSION,
        "checked_at": _utc_now_iso(),
        "blockers": blockers,
        "warnings": warnings,
    }


def _load_review(path: str) -> dict[str, Any]:
    data = load_json(path)
    if not isinstance(data, dict):
        raise ValueError("Review file must contain a JSON object.")
    return data


def _get_update_list(approved_suggestion: dict[str, Any], field_name: str) -> list[Any]:
    updates = approved_suggestion.get(field_name)
    if isinstance(updates, list):
        return updates
    return []


def _append_blank_update_field_blockers(
    blockers: list[dict[str, str]],
    approved_suggestion: dict[str, Any],
) -> None:
    for target in get_formal_state_targets():
        field_name = target.update_field
        updates = _get_update_list(approved_suggestion, field_name)
        for index, update in enumerate(updates):
            if not isinstance(update, dict):
                continue
            for update_field in ("action", "target", "content"):
                if _normalize_text(update.get(update_field)) != "":
                    continue
                blockers.append(
                    {
                        "code": "blank_update_field",
                        "message": (
                            f"approved_suggestion.{field_name}[{index}].{update_field} must be non-empty."
                        ),
                        "field": f"approved_suggestion.{field_name}[{index}].{update_field}",
                    }
                )


def _append_timeline_duplicate_blockers(
    blockers: list[dict[str, str]],
    chapter_no: int,
    timeline_updates: list[Any],
    existing_keys: set[tuple[int, str, str, str]],
) -> None:
    seen_keys: set[tuple[int, str, str, str]] = set()

    for index, update in enumerate(timeline_updates):
        if not isinstance(update, dict):
            continue

        key = (
            chapter_no,
            _normalize_text(update.get("action")),
            _normalize_text(update.get("target")),
            _normalize_text(update.get("content")),
        )
        if any(part == "" for part in key[1:]):
            continue

        if key in seen_keys or key in existing_keys:
            blockers.append(
                {
                    "code": "duplicate_timeline_update",
                    "message": (
                        f"approved_suggestion.timeline_updates[{index}] duplicates "
                        f"a timeline entry for chapter {chapter_no}."
                    ),
                    "field": f"approved_suggestion.timeline_updates[{index}]",
                }
            )
            continue

        seen_keys.add(key)


def _append_previous_summary_warning(
    warnings: list[dict[str, str]],
    project_root: str,
    chapter_no: int,
) -> None:
    if chapter_no <= 1:
        return

    previous_summary_path = get_chapter_summary_path(project_root, chapter_no - 1)
    if Path(previous_summary_path).is_file():
        return

    warnings.append(
        {
            "code": "previous_summary_missing",
            "message": f"Previous chapter summary is missing for chapter {chapter_no}.",
            "field": "previous_summary",
        }
    )


def _append_duplicate_target_warning(
    warnings: list[dict[str, str]],
    updates: list[Any],
    field_name: str,
    code: str,
) -> None:
    counts: dict[str, int] = {}
    emitted: set[str] = set()

    for update in updates:
        if not isinstance(update, dict):
            continue
        normalized_target = _normalize_text(update.get("target"))
        if normalized_target == "":
            continue
        counts[normalized_target] = counts.get(normalized_target, 0) + 1

    for update in updates:
        if not isinstance(update, dict):
            continue
        normalized_target = _normalize_text(update.get("target"))
        if normalized_target == "" or counts.get(normalized_target, 0) <= 1:
            continue
        if normalized_target in emitted:
            continue

        warnings.append(
            {
                "code": code,
                "message": (
                    f"approved_suggestion.{field_name} repeats target '{normalized_target}'."
                ),
                "field": f"approved_suggestion.{field_name}",
            }
        )
        emitted.add(normalized_target)


def _load_existing_timeline_keys(project_root: str) -> set[tuple[int, str, str, str]]:
    paths = get_project_file_paths(project_root)
    data = load_json(paths["timeline_json"])
    if not isinstance(data, dict):
        return set()

    raw_events = data.get("events")
    if not isinstance(raw_events, list):
        return set()

    keys: set[tuple[int, str, str, str]] = set()
    for item in raw_events:
        if not isinstance(item, dict):
            continue

        raw_chapter_no = item.get("chapter_no")
        if not isinstance(raw_chapter_no, int):
            continue

        action = _normalize_text(item.get("action"))
        target = _normalize_text(item.get("target"))
        content = _normalize_text(item.get("event"))
        if action == "" or target == "" or content == "":
            continue

        keys.add((raw_chapter_no, action, target, content))

    return keys


def _normalize_text(value: Any) -> str:
    return str(value).strip()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
