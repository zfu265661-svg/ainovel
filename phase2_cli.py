from __future__ import annotations

import argparse
from typing import Any, Sequence

from core.longform import initialize_loop_state, run_five_chapter_loop
from core.longform.status_service import build_project_status_report


TEXT_RUN_FAILED = "运行失败"
TEXT_ARGUMENT_ERROR = "参数错误"
DEFAULT_TARGET_CHAPTER_COUNT = 5


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="phase2_cli.py",
        description="Phase 2 longform workflow CLI entry.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser(
        "init-loop",
        help="Initialize loop_state for the 5-chapter run.",
    )
    init_parser.add_argument("--root", required=True, help="Project root path.")

    run_parser = subparsers.add_parser(
        "run-five",
        help="Run from next_chapter_no through chapter 5.",
    )
    run_parser.add_argument("--root", required=True, help="Project root path.")

    status_parser = subparsers.add_parser(
        "show-status",
        help="Show the current longform status and diagnostics.",
    )
    status_parser.add_argument("--root", required=True, help="Project root path.")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()

    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code)

    try:
        if args.command == "init-loop":
            result = initialize_loop_state(
                project_root=args.root,
                target_chapter_count=DEFAULT_TARGET_CHAPTER_COUNT,
            )
            _print_init_loop_result(args.root, result)
            return 0

        if args.command == "show-status":
            result = build_project_status_report(args.root)
            _print_show_status_result(args.root, result)
            return 0

        if args.command == "run-five":
            result = run_five_chapter_loop(args.root)
            _print_run_five_result(args.root, result)
            return 0

        print(f"{TEXT_ARGUMENT_ERROR}: unknown command")
        return 2
    except Exception as exc:
        print(f"{TEXT_RUN_FAILED}: {exc}")
        return 1


def _print_init_loop_result(project_root: str, result: dict[str, object]) -> None:
    print("初始化完成")
    print(f"project_root: {project_root}")
    print(f"start_chapter_no: {result.get('start_chapter_no')}")
    print(f"target_chapter_count: {result.get('target_chapter_count')}")
    print(f"next_chapter_no: {result.get('next_chapter_no')}")


def _print_show_status_result(project_root: str, result: dict[str, object]) -> None:
    print("当前状态")
    print(f"project_root: {project_root}")
    for key in (
        "workflow_status",
        "start_chapter_no",
        "target_chapter_count",
        "current_chapter_no",
        "next_chapter_no",
        "loop_state_last_completed_chapter_no",
        "last_successfully_committed_chapter_no",
        "last_successfully_committed_source",
        "commit_scan_status",
        "commit_loop_drift",
        "last_attempted_chapter_no",
        "last_attempt_status",
        "last_failure_stage",
        "last_error",
        "unresolved_snapshot_exists",
        "unresolved_snapshot_chapters",
        "stale_snapshot_exists",
        "stale_snapshot_chapters",
        "artifact_focus_chapter_no",
        "artifact_relation_status",
        "checkpoint_path",
        "review_path",
        "suggestion_path",
        "snapshot_path",
    ):
        print(f"{key}: {_render_value(result.get(key))}")


def _print_run_five_result(project_root: str, result: dict[str, object]) -> None:
    completed_chapters = result.get("completed_chapters")
    completed_count = len(completed_chapters) if isinstance(completed_chapters, list) else 0

    print("运行结束")
    print(f"project_root: {project_root}")
    print(f"started_from: {result.get('started_from')}")
    print(f"ended_at: {result.get('ended_at')}")
    print(f"status: {result.get('status')}")
    print(f"completed_count: {completed_count}")
    print(f"failed_chapter: {result.get('failed_chapter')}")

    if result.get("status") != "failed":
        return

    status_report = _load_status_report_or_none(project_root)
    failure_stage = _extract_run_failure_stage(result, status_report)
    print(f"failure_stage: {_render_value(failure_stage)}")
    print("next_check: checkpoint")

    if status_report is None:
        return

    for key in ("checkpoint_path", "snapshot_path", "review_path", "suggestion_path"):
        print(f"{key}: {_render_value(status_report.get(key))}")


def _load_status_report_or_none(project_root: str) -> dict[str, Any] | None:
    try:
        return build_project_status_report(project_root)
    except Exception:
        return None


def _extract_run_failure_stage(
    result: dict[str, object],
    status_report: dict[str, Any] | None,
) -> Any:
    if isinstance(status_report, dict):
        failure_stage = status_report.get("last_failure_stage")
        if failure_stage:
            return failure_stage

    per_chapter_results = result.get("per_chapter_results")
    if isinstance(per_chapter_results, list) and per_chapter_results:
        latest = per_chapter_results[-1]
        if isinstance(latest, dict):
            return latest.get("failure_stage")

    return None


def _render_value(value: object) -> str:
    if isinstance(value, list):
        return "[" + ", ".join(str(item) for item in value) + "]"
    if value is None:
        return "None"
    return str(value)


if __name__ == "__main__":
    raise SystemExit(main())
