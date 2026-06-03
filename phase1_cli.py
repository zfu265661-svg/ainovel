from __future__ import annotations

import argparse
from typing import Sequence

from core.longform.status_service import build_chapter_diagnostic_report, derive_failure_stage
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
        description="Phase 1 novel workflow CLI entry.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_parser = subparsers.add_parser(
        "create-project",
        help="Create the minimum Phase 1 project shell.",
    )
    create_parser.add_argument("--root", required=True, help="Project root path.")
    create_parser.add_argument("--title", required=True, help="Project title.")
    create_parser.add_argument("--topic", required=True, help="Project topic.")
    create_parser.add_argument("--style", required=True, help="Project style.")
    create_parser.add_argument("--target", required=True, help="Target audience or format.")

    plan_parser = subparsers.add_parser(
        "plan-novel",
        help="Generate outline, volume plan, and chapter plans.",
    )
    plan_parser.add_argument("--root", required=True, help="Project root path.")

    write_parser = subparsers.add_parser(
        "write-chapter",
        help="Generate draft, rewrite, summary, and suggestion for one chapter.",
    )
    write_parser.add_argument("--root", required=True, help="Project root path.")
    write_parser.add_argument("--chapter", required=True, type=int, help="Chapter number.")

    commit_parser = subparsers.add_parser(
        "commit-suggestion",
        help="Commit one chapter suggestion into the formal state files.",
    )
    commit_parser.add_argument("--root", required=True, help="Project root path.")
    commit_parser.add_argument("--chapter", required=True, type=int, help="Chapter number.")

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
            diagnostics = build_chapter_diagnostic_report(args.root, args.chapter)
            _print_commit_suggestion_result(args.root, result, diagnostics)
            return 0

        print(f"{TEXT_ARGUMENT_ERROR}: unknown command")
        return 2
    except Exception as exc:
        if args.command == "commit-suggestion":
            diagnostics = _load_commit_diagnostics(args.root, args.chapter, str(exc))
            _print_commit_suggestion_failure(args.root, args.chapter, str(exc), diagnostics)
            return 1
        print(f"{TEXT_RUN_FAILED}: {exc}")
        return 1


def _print_create_project_result(project_root: str, result: dict[str, object]) -> None:
    print("项目创建完成")
    print(f"project_root: {project_root}")
    print(f"{project_root}/project.json")
    print(f"{project_root}/story_bible.json")
    print(f"{project_root}/chapters.json")
    print(f"{project_root}/characters.json")
    print(f"{project_root}/timeline.json")
    print(f"{project_root}/foreshadow.json")
    print(f"{project_root}/plot_threads.json")
    print(f"{project_root}/locations.json")
    print(f"{project_root}/organizations.json")
    print(f"{project_root}/style_guide.json")
    print(f"{project_root}/scenes.json")
    print(f"{project_root}/docs/")
    print(f"{project_root}/suggestions/")
    print(f"{project_root}/exports/")
    print(f"title: {result.get('title', '')}")


def _print_plan_novel_result(project_root: str, result: dict[str, object]) -> None:
    chapters = result.get("chapters")
    chapter_count = len(chapters) if isinstance(chapters, list) else 0
    print("规划生成完成")
    print(f"project_root: {project_root}")
    print(f"{project_root}/docs/outline.md")
    print(f"{project_root}/docs/volumes.md")
    print(f"{project_root}/chapters.json")
    print(f"chapter_count: {chapter_count}")


def _print_write_chapter_result(project_root: str, result: dict[str, object]) -> None:
    print("章节生成完成")
    print(f"project_root: {project_root}")
    print(f"chapter_no: {result.get('chapter_no')}")
    print(f"draft_path: {result.get('draft_path')}")
    print(f"rewrite_path: {result.get('rewrite_path')}")
    print(f"summary_path: {result.get('summary_path')}")
    print(f"suggestion_path: {result.get('suggestion_path')}")


def _print_commit_suggestion_result(
    project_root: str,
    result: dict[str, object],
    diagnostics: dict[str, object],
) -> None:
    print("建议提交完成")
    print(f"project_root: {project_root}")
    print(f"chapter_no: {result.get('chapter_no')}")
    print(f"{project_root}/characters.json")
    print(f"{project_root}/timeline.json")
    print(f"{project_root}/foreshadow.json")
    print(f"suggestion_path: {result.get('suggestion_path')}")
    print(f"review_path: {diagnostics.get('review_path')}")
    print(f"snapshot_path: {diagnostics.get('snapshot_path')}")
    print(f"artifact_relation_status: {diagnostics.get('artifact_relation_status')}")


def _print_commit_suggestion_failure(
    project_root: str,
    chapter_no: int,
    error_message: str,
    diagnostics: dict[str, object],
) -> None:
    print(f"{TEXT_RUN_FAILED}: {error_message}")
    print(f"project_root: {project_root}")
    print(f"chapter_no: {chapter_no}")
    print(f"failure_stage: {diagnostics.get('failure_stage')}")
    print(f"suggestion_path: {diagnostics.get('suggestion_path')}")
    print(f"review_path: {diagnostics.get('review_path')}")
    print(f"snapshot_path: {diagnostics.get('snapshot_path')}")
    print(f"artifact_relation_status: {diagnostics.get('artifact_relation_status')}")


def _load_commit_diagnostics(
    project_root: str,
    chapter_no: int,
    error_message: str,
) -> dict[str, object]:
    try:
        diagnostics = build_chapter_diagnostic_report(project_root, chapter_no)
    except Exception:
        diagnostics = {
            "artifact_relation_status": "unknown",
            "review_path": None,
            "suggestion_path": None,
            "snapshot_path": None,
            "failure_stage": None,
        }

    return {
        **diagnostics,
        "failure_stage": diagnostics.get("failure_stage")
        or derive_failure_stage(error_message, default_stage="unknown"),
    }


if __name__ == "__main__":
    raise SystemExit(main())
