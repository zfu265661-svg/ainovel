from __future__ import annotations

import argparse
import json
from typing import Any

from application.use_cases.create_project import create_project
from application.use_cases.inspect_context import inspect_context, inspect_report, inspect_trace
from application.use_cases.run_chapter import run_chapter


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="novel-engine")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init-project")
    init.add_argument("--name", required=True)
    init.add_argument("--project-id")

    run = sub.add_parser("run-chapter")
    run.add_argument("--project-id", required=True)
    run.add_argument("--chapter-id", required=True, type=int)
    run.add_argument("--dry-run", action="store_true")
    run.add_argument("--review-before-commit", action="store_true")

    for name in ("inspect-context", "inspect-trace", "inspect-report"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--project-id", required=True)
        cmd.add_argument("--chapter-id", required=True, type=int)

    args = parser.parse_args(argv)
    if args.command == "init-project":
        _print(create_project(args.name, project_id=args.project_id))
    elif args.command == "run-chapter":
        _print(run_chapter(args.project_id, args.chapter_id, dry_run=args.dry_run, review_before_commit=args.review_before_commit))
    elif args.command == "inspect-context":
        _print(inspect_context(args.project_id, args.chapter_id))
    elif args.command == "inspect-trace":
        _print(inspect_trace(args.project_id, args.chapter_id))
    elif args.command == "inspect-report":
        _print(inspect_report(args.project_id, args.chapter_id))


def _print(payload: Any) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
