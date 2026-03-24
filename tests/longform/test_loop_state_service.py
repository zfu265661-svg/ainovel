from __future__ import annotations

import pytest

from core.longform.loop_state_service import (
    STATUS_COMPLETED,
    STATUS_READY,
    STATUS_RUNNING,
    create_loop_state,
    get_resume_chapter_no,
    mark_chapter_completed,
    mark_chapter_started,
)


def test_create_loop_state_returns_minimum_resume_friendly_shape() -> None:
    state = create_loop_state(target_chapter_count=5, start_chapter_no=1)

    assert state == {
        "version": 1,
        "status": STATUS_READY,
        "start_chapter_no": 1,
        "target_chapter_count": 5,
        "next_chapter_no": 1,
        "last_completed_chapter_no": 0,
        "current_chapter_no": None,
    }
    assert get_resume_chapter_no(state) == 1


def test_mark_chapter_started_keeps_resume_pointer_on_next_chapter() -> None:
    state = create_loop_state(target_chapter_count=5, start_chapter_no=1)

    running_state = mark_chapter_started(state)

    assert running_state["status"] == STATUS_RUNNING
    assert running_state["current_chapter_no"] == 1
    assert running_state["next_chapter_no"] == 1
    assert get_resume_chapter_no(running_state) == 1


def test_mark_chapter_completed_advances_resume_pointer_only_after_commit() -> None:
    state = create_loop_state(target_chapter_count=2, start_chapter_no=3)
    running_state = mark_chapter_started(state, chapter_no=3)

    completed_state = mark_chapter_completed(running_state, chapter_no=3)
    final_state = mark_chapter_completed(
        mark_chapter_started(completed_state, chapter_no=4),
        chapter_no=4,
    )

    assert completed_state["status"] == STATUS_READY
    assert completed_state["last_completed_chapter_no"] == 3
    assert completed_state["next_chapter_no"] == 4
    assert get_resume_chapter_no(completed_state) == 4
    assert final_state["status"] == STATUS_COMPLETED
    assert final_state["next_chapter_no"] == 5


def test_mark_chapter_completed_rejects_out_of_order_progress() -> None:
    state = create_loop_state(target_chapter_count=5, start_chapter_no=1)

    with pytest.raises(ValueError, match="next_chapter_no=1"):
        mark_chapter_completed(state, chapter_no=2)
