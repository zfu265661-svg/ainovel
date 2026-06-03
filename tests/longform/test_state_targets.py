from __future__ import annotations

from core.longform.state_targets import (
    get_formal_state_targets,
    get_required_suggestion_update_fields,
)


def test_formal_state_targets_lock_current_commit_surface() -> None:
    targets = get_formal_state_targets()

    assert [target.name for target in targets] == [
        "characters",
        "timeline",
        "foreshadow",
    ]
    assert [target.path_key for target in targets] == [
        "characters_json",
        "timeline_json",
        "foreshadow_json",
    ]
    assert get_required_suggestion_update_fields() == (
        "character_updates",
        "timeline_updates",
        "foreshadow_updates",
    )
