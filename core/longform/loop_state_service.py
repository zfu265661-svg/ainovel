from __future__ import annotations

from typing import Any

from core.storage import load_json, save_json


STATE_VERSION = 1
STATUS_READY = "ready"
STATUS_RUNNING = "running"
STATUS_FAILED = "failed"
STATUS_COMPLETED = "completed"
REQUIRED_FIELDS: tuple[str, ...] = (
    "version",
    "status",
    "start_chapter_no",
    "target_chapter_count",
    "next_chapter_no",
    "last_completed_chapter_no",
    "current_chapter_no",
)
VALID_STATUSES = {
    STATUS_READY,
    STATUS_RUNNING,
    STATUS_FAILED,
    STATUS_COMPLETED,
}


def create_loop_state(
    target_chapter_count: int,
    start_chapter_no: int = 1,
) -> dict[str, Any]:
    """Create the minimum loop state used to resume longform execution safely."""
    _validate_positive_int("target_chapter_count", target_chapter_count)
    _validate_positive_int("start_chapter_no", start_chapter_no)

    return {
        "version": STATE_VERSION,
        "status": STATUS_READY,
        "start_chapter_no": start_chapter_no,
        "target_chapter_count": target_chapter_count,
        "next_chapter_no": start_chapter_no,
        "last_completed_chapter_no": start_chapter_no - 1,
        "current_chapter_no": None,
    }


def load_loop_state(path: str) -> dict[str, Any]:
    """Load and validate loop progress state from JSON."""
    data = load_json(path)
    if not isinstance(data, dict):
        raise ValueError(f"Loop state file must contain a JSON object: {path}")

    _validate_loop_state(data)
    return data


def save_loop_state(path: str, state: dict[str, Any]) -> None:
    """Validate and persist loop progress state to JSON."""
    _validate_loop_state(state)
    save_json(path, state)


def get_resume_chapter_no(state: dict[str, Any]) -> int:
    """Resume always starts from next_chapter_no after the last committed chapter."""
    _validate_loop_state(state)
    return int(state["next_chapter_no"])


def mark_chapter_started(
    state: dict[str, Any],
    chapter_no: int | None = None,
) -> dict[str, Any]:
    """Mark one chapter as running without advancing the resume pointer."""
    _validate_loop_state(state)
    target_chapter_no = get_resume_chapter_no(state) if chapter_no is None else chapter_no
    _validate_positive_int("chapter_no", target_chapter_no)

    if target_chapter_no != state["next_chapter_no"]:
        raise ValueError(
            f"Loop state can only start next_chapter_no={state['next_chapter_no']}, "
            f"got {target_chapter_no}."
        )

    return {
        **state,
        "status": STATUS_RUNNING,
        "current_chapter_no": target_chapter_no,
    }


def mark_chapter_completed(state: dict[str, Any], chapter_no: int) -> dict[str, Any]:
    """Advance loop progress only after a chapter has been fully committed."""
    _validate_loop_state(state)
    _validate_positive_int("chapter_no", chapter_no)

    if chapter_no != state["next_chapter_no"]:
        raise ValueError(
            f"Loop state can only complete next_chapter_no={state['next_chapter_no']}, "
            f"got {chapter_no}."
        )

    final_chapter_no = _get_final_chapter_no(state)
    next_chapter_no = chapter_no + 1
    status = STATUS_COMPLETED if chapter_no >= final_chapter_no else STATUS_READY

    return {
        **state,
        "status": status,
        "current_chapter_no": None,
        "last_completed_chapter_no": chapter_no,
        "next_chapter_no": next_chapter_no,
    }


def mark_chapter_failed(state: dict[str, Any], chapter_no: int) -> dict[str, Any]:
    """Persist a failed chapter marker while keeping resume on next_chapter_no."""
    _validate_loop_state(state)
    _validate_positive_int("chapter_no", chapter_no)

    return {
        **state,
        "status": STATUS_FAILED,
        "current_chapter_no": chapter_no,
    }


def _validate_loop_state(state: dict[str, Any]) -> None:
    missing_fields = [field for field in REQUIRED_FIELDS if field not in state]
    if missing_fields:
        missing = ", ".join(missing_fields)
        raise ValueError(f"Loop state is missing required field(s): {missing}")

    if state["version"] != STATE_VERSION:
        raise ValueError(f"Unsupported loop state version: {state['version']}")

    if state["status"] not in VALID_STATUSES:
        raise ValueError(f"Unsupported loop state status: {state['status']}")

    _validate_positive_int("start_chapter_no", state["start_chapter_no"])
    _validate_positive_int("target_chapter_count", state["target_chapter_count"])
    _validate_positive_int("next_chapter_no", state["next_chapter_no"])

    last_completed_chapter_no = state["last_completed_chapter_no"]
    if not isinstance(last_completed_chapter_no, int):
        raise ValueError("loop_state.last_completed_chapter_no must be an integer.")

    current_chapter_no = state["current_chapter_no"]
    if current_chapter_no is not None and not isinstance(current_chapter_no, int):
        raise ValueError("loop_state.current_chapter_no must be an integer or null.")

    minimum_last_completed = state["start_chapter_no"] - 1
    if last_completed_chapter_no < minimum_last_completed:
        raise ValueError(
            "loop_state.last_completed_chapter_no cannot be before start_chapter_no - 1."
        )

    if state["next_chapter_no"] != last_completed_chapter_no + 1:
        raise ValueError(
            "loop_state.next_chapter_no must equal last_completed_chapter_no + 1."
        )

    final_chapter_no = _get_final_chapter_no(state)
    if state["next_chapter_no"] > final_chapter_no + 1:
        raise ValueError("loop_state.next_chapter_no exceeds the configured loop range.")

    if current_chapter_no is not None and current_chapter_no < state["start_chapter_no"]:
        raise ValueError("loop_state.current_chapter_no cannot be before start_chapter_no.")


def _get_final_chapter_no(state: dict[str, Any]) -> int:
    return state["start_chapter_no"] + state["target_chapter_count"] - 1


def _validate_positive_int(name: str, value: Any) -> None:
    if not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer.")
