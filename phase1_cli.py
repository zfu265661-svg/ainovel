from __future__ import annotations

import argparse
from typing import Sequence

from core.workflow_service import (
    commit_suggestion,
    create_project,
    plan_novel,
    write_chapter,
)


TEXT_RUN_FAILED = "运行失败"
TEXT_ARGUMENT_ERROR = "参数错误"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="phase1_cli.py",
        description="Phase 1 小说工作台命令行入口，不替代旧 app.py。",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_parser = subparsers.add_parser(
        "create-project",
        help="创建 Phase 1 小说项目壳子。",
    )
    create_parser.add_argument("--root", required=True, help="项目根目录。")
    create_parser.add_argument("--title", required=True, help="项目标题。")
    create_parser.add_argument("--topic", required=True, help="题材。")
    create_parser.add_argument("--style", required=True, help="风格。")
    create_parser.add_argument("--target", required=True, help="目标读者或篇幅方向。")

    plan_parser = subparsers.add_parser(
        "plan-novel",
        help="生成并落盘总纲、分卷和章节规划。",
    )
    plan_parser.add_argument("--root", required=True, help="项目根目录。")

    write_parser = subparsers.add_parser(
        "write-chapter",
        help="为指定章节生成正文、改写、摘要和建议。",
    )
    write_parser.add_argument("--root", required=True, help="项目根目录。")
    write_parser.add_argument("--chapter", required=True, type=int, help="章节号。")

    commit_parser = subparsers.add_parser(
        "commit-suggestion",
        help="将指定章节的 suggestion 提交到正式状态文件。",
    )
    commit_parser.add_argument("--root", required=True, help="项目根目录。")
    commit_parser.add_argument("--chapter", required=True, type=int, help="章节号。")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()

    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code)

    try:
        if args.command == "create-project":
            result = create_project(
                project_root=args.root,
                title=args.title,
                topic=args.topic,
                style=args.style,
                target=args.target,
            )
            _print_create_project_result(args.root, result)
            return 0

        if args.command == "plan-novel":
            result = plan_novel(args.root)
            _print_plan_novel_result(args.root, result)
            return 0

        if args.command == "write-chapter":
            result = write_chapter(args.root, args.chapter)
            _print_write_chapter_result(args.root, result)
            return 0

        if args.command == "commit-suggestion":
            result = commit_suggestion(args.root, args.chapter)
            _print_commit_suggestion_result(args.root, result)
            return 0

        print(f"{TEXT_ARGUMENT_ERROR}: unknown command")
        return 2
    except Exception as exc:
        print(f"{TEXT_RUN_FAILED}: {exc}")
        return 1


def _print_create_project_result(project_root: str, result: dict[str, object]) -> None:
    print("项目创建完成。")
    print(f"项目路径: {project_root}")
    print("已创建:")
    print(f"- {project_root}/project.json")
    print(f"- {project_root}/chapters.json")
    print(f"- {project_root}/characters.json")
    print(f"- {project_root}/timeline.json")
    print(f"- {project_root}/foreshadow.json")
    print(f"- {project_root}/docs/")
    print(f"- {project_root}/suggestions/")
    print(f"项目标题: {result.get('title', '')}")


def _print_plan_novel_result(project_root: str, result: dict[str, object]) -> None:
    chapters = result.get("chapters")
    chapter_count = len(chapters) if isinstance(chapters, list) else 0
    print("规划生成完成。")
    print(f"项目路径: {project_root}")
    print("已生成:")
    print(f"- {project_root}/docs/outline.md")
    print(f"- {project_root}/docs/volumes.md")
    print(f"- {project_root}/chapters.json")
    print(f"- 章节规划文档数量: {chapter_count}")


def _print_write_chapter_result(project_root: str, result: dict[str, object]) -> None:
    print("章节生成完成。")
    print(f"项目路径: {project_root}")
    print(f"章节号: {result.get('chapter_no')}")
    print("已生成:")
    print(f"- {result.get('draft_path')}")
    print(f"- {result.get('rewrite_path')}")
    print(f"- {result.get('summary_path')}")
    print(f"- {result.get('suggestion_path')}")


def _print_commit_suggestion_result(project_root: str, result: dict[str, object]) -> None:
    print("建议提交完成。")
    print(f"项目路径: {project_root}")
    print(f"章节号: {result.get('chapter_no')}")
    print("已更新:")
    print(f"- {project_root}/characters.json")
    print(f"- {project_root}/timeline.json")
    print(f"- {project_root}/foreshadow.json")
    print(f"- {result.get('suggestion_path')}")


if __name__ == "__main__":
    raise SystemExit(main())
