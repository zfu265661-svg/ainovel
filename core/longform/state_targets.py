from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StateTarget:
    """Canonical formal-state target controlled by review/commit/snapshot."""

    name: str
    path_key: str
    item_key: str
    update_field: str
    result_count_key: str
    restore_error_label: str
    duplicate_warning_code: str | None = None


FORMAL_STATE_TARGETS: tuple[StateTarget, ...] = (
    StateTarget(
        name="characters",
        path_key="characters_json",
        item_key="characters",
        update_field="character_updates",
        result_count_key="characters_updated",
        restore_error_label="characters restore failed",
        duplicate_warning_code="duplicate_character_target",
    ),
    StateTarget(
        name="timeline",
        path_key="timeline_json",
        item_key="events",
        update_field="timeline_updates",
        result_count_key="timeline_updated",
        restore_error_label="timeline restore failed",
    ),
    StateTarget(
        name="foreshadow",
        path_key="foreshadow_json",
        item_key="items",
        update_field="foreshadow_updates",
        result_count_key="foreshadow_updated",
        restore_error_label="foreshadow restore failed",
        duplicate_warning_code="duplicate_foreshadow_target",
    ),
)


def get_formal_state_targets() -> tuple[StateTarget, ...]:
    return FORMAL_STATE_TARGETS


def get_required_suggestion_update_fields() -> tuple[str, ...]:
    return tuple(target.update_field for target in FORMAL_STATE_TARGETS)
