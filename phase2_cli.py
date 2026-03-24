from __future__ import annotations

import argparse
from typing import Sequence

from core.longform import (
    initialize_loop_state,
    load_project_loop_state,
    run_five_chapter_loop,
)


TEXT_RUN_FAILED = "运行失败"
TEXT_ARGUMENT_ERROR = "参数错误"
DEFAULT_TARGET_CHAPTER_COUNT = 5


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="phase2_cli.py",
        description="Phase 2 longform 工作流命令行入口，不替代旧入口。",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser(
        "init-loop",
        help="初始化 longform loop_state。",
    )
    init_parser.add_argument("--root", required=True, help="项目根目录。")

    run_parser = subparsers.add_parser(
        "run-five",
        help="从当前 next_chapter_no 开始顺序运行到第 5 章。",
    )
    run_parser.add_argument("--root", required=True, help="项目根目录。")

    status_parser = subparsers.add_parser(
        "show-status",
        help="显示当前 loop_state 的关键信息。",
    )
    status_parser.add_argument("--root", required=True, help="项目根目录。")

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
            result = load_project_loop_state(args.root)
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
    print("初始化完成。")
    print(f"项目路径: {project_root}")
    print(f"起始章节: {result.get('start_chapter_no')}")
    print(f"目标章节数: {result.get('target_chapter_count')}")
    print(f"下一章节: {result.get('next_chapter_no')}")


def _print_show_status_result(project_root: str, result: dict[str, object]) -> None:
    print("当前状态。")
    print(f"项目路径: {project_root}")
    print(f"状态: {result.get('status')}")
    print(f"起始章节: {result.get('start_chapter_no')}")
    print(f"目标章节数: {result.get('target_chapter_count')}")
    print(f"下一章节: {result.get('next_chapter_no')}")
    print(f"已完成到: {result.get('last_completed_chapter_no')}")
    print(f"当前运行章节: {result.get('current_chapter_no')}")


def _print_run_five_result(project_root: str, result: dict[str, object]) -> None:
    completed_chapters = result.get("completed_chapters")
    completed_count = len(completed_chapters) if isinstance(completed_chapters, list) else 0

    print("运行结束。")
    print(f"项目路径: {project_root}")
    print(f"开始章节: {result.get('started_from')}")
    print(f"结束章节: {result.get('ended_at')}")
    print(f"状态: {result.get('status')}")
    print(f"完成章节数: {completed_count}")
    print(f"失败章节: {result.get('failed_chapter')}")


if __name__ == "__main__":
    raise SystemExit(main())
