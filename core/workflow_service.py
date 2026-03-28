from __future__ import annotations

import json
from copy import deepcopy
from importlib import import_module
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Protocol, TypeVar, cast

from core.character_service import load_characters
from core.chapter_service import generate_chapter_plan
from core.chapter_service import generate_volume_chapters
from core.draft_service import generate_draft
from core.errors import NovelAgentError
from core.foreshadow_service import load_foreshadows
from core.longform.chapter_context_service import build_chapter_context
from core.longform.consistency_service import run_review_consistency_check
from core.longform.project_state_repository import get_chapter_review_path
from core.longform.review_service import create_or_refresh_review, load_review_for_commit
from core.longform.snapshot_service import (
    cleanup_snapshot_after_commit,
    create_pending_snapshot,
    handle_preflight_snapshot,
    recover_failed_commit_with_snapshot,
)
from core.outline_service import generate_outline
from core.project_service import (
    get_chapter_draft_path,
    create_project_structure,
    get_chapter_plan_path,
    get_chapter_rewrite_path,
    get_chapter_summary_path,
    get_chapter_suggestion_path,
    get_project_file_paths,
    load_project,
)
from core.rewrite_service import rewrite_text
from core.storage import load_json, load_text, save_json, save_text
from core.suggestion_service import generate_state_suggestions
from core.summarizer import summarize_previous_chapter
from core.timeline_service import load_timeline
from core.volume_service import generate_volume_plan


class WorkflowServiceError(NovelAgentError, RuntimeError):
    """Raised when the basic novel workflow fails."""


class _RewriteModule(Protocol):
    def rewrite_text(self, text: str) -> str:
        ...


class _CheckerModule(Protocol):
    def check_consistency(
        self,
        draft_text: str,
        outline: dict[str, Any],
        character_info: dict[str, Any],
        timeline: list[Any],
    ) -> dict[str, Any]:
        ...


class _StorageModule(Protocol):
    def save_json(self, path: str, data: dict[str, Any]) -> None:
        ...


T = TypeVar("T")


def create_project(
    project_root: str,
    title: str,
    topic: str,
    style: str,
    target: str,
) -> dict[str, Any]:
    """Create the minimum Phase 1 project shell."""
    return create_project_structure(
        project_root=project_root,
        title=title,
        topic=topic,
        style=style,
        target=target,
    )


def plan_novel(project_root: str) -> dict[str, Any]:
    """Generate and persist outline, volume plan, and chapter plans for a project."""
    project = _run_stage("project load", lambda: load_project(project_root))
    outline = _generate_outline_stage(
        topic=str(project["topic"]),
        style=str(project["style"]),
        target=str(project["target"]),
    )
    volume_plan = _run_stage(
        "volume plan generation",
        lambda: generate_volume_plan(outline),
    )
    chapter_plans = _generate_volume_chapter_plans(outline, volume_plan)
    chapter_index = [_to_chapter_index_entry(chapter_plan) for chapter_plan in chapter_plans]

    _persist_phase1_plan(
        project_root=project_root,
        outline=outline,
        volume_plan=volume_plan,
        chapter_plans=chapter_plans,
        chapter_index=chapter_index,
    )

    return {
        "project": project,
        "outline": outline,
        "volume_plan": volume_plan,
        "chapters": chapter_index,
    }


def write_chapter(project_root: str, chapter_no: int) -> dict[str, Any]:
    """Generate and persist all Phase 1 chapter outputs for one planned chapter."""
    project = _run_stage("project load", lambda: load_project(project_root))
    paths = get_project_file_paths(project_root)
    outline = _run_stage("outline load", lambda: _load_outline_from_project(paths))
    chapters_index = _run_stage("chapter index load", lambda: _load_chapter_index(paths))
    chapter_entry = _run_stage(
        "chapter lookup",
        lambda: _find_chapter_entry(chapters_index, chapter_no),
    )
    chapter_plan = _run_stage(
        "chapter plan load",
        lambda: _load_chapter_plan_from_project(project_root, chapter_no),
    )
    previous_summary = _load_previous_summary(project_root, chapter_no)
    characters = _run_stage("character state load", lambda: _load_character_state(paths))
    timeline = _run_stage("timeline state load", lambda: _load_timeline_state(paths))
    foreshadow = _run_stage("foreshadow state load", lambda: _load_foreshadow_state(paths))

    context_bundle = _run_stage(
        "draft context assembly",
        lambda: build_chapter_context(
            chapter_no=chapter_no,
            outline=outline,
            previous_summary=previous_summary,
            characters=characters,
            timeline=timeline,
            foreshadow=foreshadow,
        ),
    )
    draft_text = _run_stage(
        "draft generation",
        lambda: generate_draft(
            chapter_plan=chapter_plan,
            context_bundle=context_bundle,
            style_rules=str(project["style"]),
        ),
    )
    rewritten_text = _run_stage("draft rewrite", lambda: rewrite_text(draft_text))
    chapter_summary = _run_stage(
        "chapter summarization",
        lambda: summarize_previous_chapter(rewritten_text),
    )
    suggestion = _run_stage(
        "state suggestion generation",
        lambda: generate_state_suggestions(
            chapter_no=chapter_no,
            outline=outline,
            chapter_plan=chapter_plan,
            rewritten_text=rewritten_text,
            chapter_summary=chapter_summary,
            characters=characters,
            timeline=timeline,
            foreshadow=foreshadow,
        ),
    )

    draft_path = get_chapter_draft_path(project_root, chapter_no)
    rewrite_path = get_chapter_rewrite_path(project_root, chapter_no)
    summary_path = get_chapter_summary_path(project_root, chapter_no)
    suggestion_path = get_chapter_suggestion_path(project_root, chapter_no)

    _run_stage("draft persistence", lambda: save_text(draft_path, draft_text))
    _run_stage("rewrite persistence", lambda: save_text(rewrite_path, rewritten_text))
    _run_stage("summary persistence", lambda: save_text(summary_path, chapter_summary))
    _run_stage("suggestion persistence", lambda: save_json(suggestion_path, suggestion))

    return {
        "chapter_no": cast(int, chapter_entry["chapter_no"]),
        "draft_path": draft_path,
        "rewrite_path": rewrite_path,
        "summary_path": summary_path,
        "suggestion_path": suggestion_path,
    }


def commit_suggestion(project_root: str, chapter_no: int) -> dict[str, Any]:
    """Commit one chapter suggestion file into the formal state JSON files."""
    paths = get_project_file_paths(project_root)
    suggestion_path = get_chapter_suggestion_path(project_root, chapter_no)
    preflight_result = _run_stage(
        "preflight snapshot handling",
        lambda: handle_preflight_snapshot(project_root, chapter_no),
    )
    if isinstance(preflight_result, dict) and preflight_result.get("status") == "already_committed":
        approved_suggestion = cast(dict[str, Any], preflight_result["approved_suggestion"])
        return _build_commit_result_from_suggestion(
            suggestion=approved_suggestion,
            chapter_no=chapter_no,
            suggestion_path=suggestion_path,
        )

    _run_stage(
        "suggestion load",
        lambda: _load_suggestion_for_commit(suggestion_path, chapter_no),
    )
    _run_stage(
        "review creation",
        lambda: create_or_refresh_review(project_root, chapter_no),
    )
    _run_stage(
        "review consistency check",
        lambda: run_review_consistency_check(project_root, chapter_no),
    )
    review = _run_stage(
        "review load",
        lambda: load_review_for_commit(project_root, chapter_no),
    )
    approved_suggestion = cast(dict[str, Any], review["approved_suggestion"])
    prepared_commit = _prepare_preloaded_suggestion_commit(
        paths=paths,
        suggestion=approved_suggestion,
        chapter_no=chapter_no,
        suggestion_path=suggestion_path,
    )
    _run_stage(
        "snapshot persistence",
        lambda: create_pending_snapshot(
            project_root=project_root,
            chapter_no=chapter_no,
            review_path=get_chapter_review_path(project_root, chapter_no),
            suggestion_path=suggestion_path,
            state_before=cast(dict[str, Any], prepared_commit["state_before"]),
        ),
    )

    try:
        _persist_prepared_formal_state(
            paths=paths,
            state_after=cast(dict[str, dict[str, Any]], prepared_commit["state_after"]),
        )
        _run_stage(
            "commit marker persistence",
            lambda: _persist_commit_markers(
                project_root=project_root,
                chapter_no=chapter_no,
                review=review,
            ),
        )
    except Exception as exc:
        try:
            _run_stage(
                "commit restore",
                lambda: recover_failed_commit_with_snapshot(
                    project_root=project_root,
                    chapter_no=chapter_no,
                    failure_reason=str(exc),
                ),
            )
        except Exception:
            raise
        raise

    _run_stage(
        "snapshot cleanup",
        lambda: cleanup_snapshot_after_commit(project_root, chapter_no),
    )
    return cast(dict[str, Any], prepared_commit["result"])


def _prepare_preloaded_suggestion_commit(
    paths: dict[str, str],
    suggestion: dict[str, Any],
    chapter_no: int,
    suggestion_path: str,
) -> dict[str, Any]:
    characters_payload, characters_state = _run_stage(
        "character state load",
        lambda: _load_state_payload_and_items(paths["characters_json"], "characters"),
    )
    timeline_payload, timeline_state = _run_stage(
        "timeline state load",
        lambda: _load_state_payload_and_items(paths["timeline_json"], "events"),
    )
    foreshadow_payload, foreshadow_state = _run_stage(
        "foreshadow state load",
        lambda: _load_state_payload_and_items(paths["foreshadow_json"], "items"),
    )

    updated_characters = _apply_character_updates(
        characters_state,
        cast(list[dict[str, Any]], suggestion["character_updates"]),
    )
    updated_timeline = _apply_timeline_updates(
        timeline_state,
        cast(list[dict[str, Any]], suggestion["timeline_updates"]),
        chapter_no,
    )
    updated_foreshadow = _apply_foreshadow_updates(
        foreshadow_state,
        cast(list[dict[str, Any]], suggestion["foreshadow_updates"]),
        chapter_no,
    )

    return {
        "state_before": {
            "characters": deepcopy(characters_payload),
            "timeline": deepcopy(timeline_payload),
            "foreshadow": deepcopy(foreshadow_payload),
        },
        "state_after": {
            "characters": {"characters": updated_characters},
            "timeline": {"events": updated_timeline},
            "foreshadow": {"items": updated_foreshadow},
        },
        "result": _build_commit_result_from_suggestion(
            suggestion=suggestion,
            chapter_no=chapter_no,
            suggestion_path=suggestion_path,
        ),
    }


def _persist_commit_markers(
    project_root: str,
    chapter_no: int,
    review: dict[str, Any],
) -> None:
    suggestion_path = get_chapter_suggestion_path(project_root, chapter_no)
    review_path = get_chapter_review_path(project_root, chapter_no)
    suggestion = _load_suggestion_for_commit(suggestion_path, chapter_no)
    original_review = dict(review)

    committed_review = {
        **original_review,
        "committed": True,
        "committed_chapter_no": chapter_no,
    }
    committed_suggestion = {
        **suggestion,
        "committed": True,
        "committed_chapter_no": chapter_no,
    }

    save_json(review_path, committed_review)
    save_json(suggestion_path, committed_suggestion)


def run_basic_workflow(
    topic: str,
    style: str,
    target: str,
    chapter_no: int = 1,
    previous_summary: str = "",
) -> dict[str, Any]:
    """Run the minimum novel workflow from outline generation to optional rewrite."""
    outline = _generate_outline_stage(
        topic=topic,
        style=style,
        target=target,
    )
    chapter_plan = _generate_chapter_plan_stage(
        outline=outline,
        chapter_no=chapter_no,
        previous_summary=previous_summary,
    )
    draft = _generate_draft_stage(
        chapter_plan=chapter_plan,
        outline=outline,
        style=style,
    )
    rewritten_draft = _rewrite_draft_if_available(draft)

    return _build_workflow_result(
        outline=outline,
        chapter_plan=chapter_plan,
        draft=draft,
        rewritten_draft=rewritten_draft,
    )


def run_basic_workflow_with_consistency_check(
    topic: str,
    style: str,
    target: str,
    chapter_no: int = 1,
    previous_summary: str = "",
) -> dict[str, Any]:
    """Run the basic workflow and append a consistency check result."""
    result = run_basic_workflow(
        topic=topic,
        style=style,
        target=target,
        chapter_no=chapter_no,
        previous_summary=previous_summary,
    )
    consistency_check = _run_consistency_check_stage(result)
    return _attach_consistency_check(result, consistency_check)


def save_workflow_result(path: str, result: dict[str, Any]) -> bool:
    """Persist workflow output if the optional storage module is available."""
    storage_module = _load_optional_module("core.storage")
    if storage_module is None:
        return False

    typed_storage = cast(_StorageModule, storage_module)
    try:
        typed_storage.save_json(path, result)
    except Exception as exc:
        raise WorkflowServiceError(
            f"Failed to save workflow result to '{path}': {exc}"
        ) from exc

    return True


def _generate_outline_stage(topic: str, style: str, target: str) -> dict[str, Any]:
    return _run_stage(
        "outline generation",
        lambda: generate_outline(topic=topic, style=style, target=target),
    )


def _generate_volume_chapter_plans(
    outline: dict[str, Any],
    volume_plan: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    chapter_plans: list[dict[str, Any]] = []
    next_chapter_no = 1

    for volume_info in volume_plan:
        volume_chapters = _run_stage(
            "volume chapter planning",
            lambda volume_info=volume_info, next_chapter_no=next_chapter_no: generate_volume_chapters(
                outline=outline,
                volume_info=volume_info,
                start_chapter_no=next_chapter_no,
            ),
        )
        chapter_plans.extend(volume_chapters)
        next_chapter_no += len(volume_chapters)

    return chapter_plans


def _generate_chapter_plan_stage(
    outline: dict[str, Any],
    chapter_no: int,
    previous_summary: str,
) -> dict[str, Any]:
    return _run_stage(
        "chapter plan generation",
        lambda: generate_chapter_plan(
            outline=outline,
            chapter_no=chapter_no,
            previous_summary=previous_summary,
        ),
    )


def _generate_draft_stage(
    chapter_plan: dict[str, Any],
    outline: dict[str, Any],
    style: str,
) -> str:
    return _run_stage(
        "draft generation",
        lambda: generate_draft(
            chapter_plan=chapter_plan,
            character_info=_project_protagonist(outline),
            style_rules=style,
        ),
    )


def _run_stage(stage_name: str, action: Callable[[], T]) -> T:
    try:
        return action()
    except WorkflowServiceError:
        raise
    except Exception as exc:
        raise WorkflowServiceError(f"Failed during {stage_name}: {exc}") from exc


def _rewrite_draft_if_available(draft: str) -> str | None:
    rewrite_module = _load_optional_rewrite_module()
    if rewrite_module is None:
        return None

    return _run_stage("draft rewrite", lambda: rewrite_module.rewrite_text(draft))


def _run_consistency_check_stage(result: dict[str, Any]) -> dict[str, Any]:
    checker_module = _load_checker_module()
    return _run_stage(
        "consistency check",
        lambda: checker_module.check_consistency(
            draft_text=_select_draft_for_consistency_check(result),
            outline=result["outline"],
            character_info=_project_protagonist(result["outline"]),
            timeline=_load_timeline_history(result),
        ),
    )


def _load_optional_rewrite_module() -> _RewriteModule | None:
    rewrite_module = _load_optional_module("core.rewrite_service")
    if rewrite_module is None:
        return None
    return cast(_RewriteModule, rewrite_module)


def _load_checker_module() -> _CheckerModule:
    checker_module = _load_optional_module("core.checker_service")
    if checker_module is None:
        raise WorkflowServiceError("Failed during consistency check: checker service is not available.")
    return cast(_CheckerModule, checker_module)


def _project_protagonist(outline: dict[str, Any]) -> dict[str, Any]:
    protagonist = outline.get("protagonist")
    if isinstance(protagonist, dict):
        return protagonist
    return {}


def _select_draft_for_consistency_check(result: dict[str, Any]) -> str:
    rewritten_draft = result.get("rewritten_draft")
    if isinstance(rewritten_draft, str) and rewritten_draft:
        return rewritten_draft
    return cast(str, result["draft"])


def _load_timeline_history(result: dict[str, Any]) -> list[Any]:
    chapter_no = _extract_chapter_no(result.get("chapter_plan"))
    try:
        timeline = load_timeline()
    except FileNotFoundError:
        return []

    if chapter_no is None:
        return timeline

    return [
        event
        for event in timeline
        if isinstance(event, dict) and event.get("chapter_no") is not None and event.get("chapter_no") < chapter_no
    ]


def _extract_chapter_no(chapter_plan: Any) -> int | None:
    if not isinstance(chapter_plan, dict):
        return None

    chapter_no = chapter_plan.get("chapter_no")
    if isinstance(chapter_no, int):
        return chapter_no

    return None


def _build_workflow_result(
    outline: dict[str, Any],
    chapter_plan: dict[str, Any],
    draft: str,
    rewritten_draft: str | None,
) -> dict[str, Any]:
    return {
        "outline": outline,
        "chapter_plan": chapter_plan,
        "draft": draft,
        "rewritten_draft": rewritten_draft,
    }


def _attach_consistency_check(
    result: dict[str, Any],
    consistency_check: dict[str, Any],
) -> dict[str, Any]:
    return {
        **result,
        "consistency_check": consistency_check,
    }


def _persist_phase1_plan(
    project_root: str,
    outline: dict[str, Any],
    volume_plan: list[dict[str, Any]],
    chapter_plans: list[dict[str, Any]],
    chapter_index: list[dict[str, Any]],
) -> None:
    paths = get_project_file_paths(project_root)
    docs_dir = Path(paths["docs_dir"])

    _run_stage(
        "outline persistence",
        lambda: save_text(
            str(docs_dir / "outline.md"),
            _render_outline_markdown(outline),
        ),
    )
    _run_stage(
        "volume plan persistence",
        lambda: save_text(
            str(docs_dir / "volumes.md"),
            _render_volumes_markdown(volume_plan),
        ),
    )
    _run_stage(
        "chapter index persistence",
        lambda: save_json(paths["chapters_json"], {"chapters": chapter_index}),
    )

    for chapter_plan in chapter_plans:
        chapter_no = cast(int, chapter_plan["chapter_no"])
        _run_stage(
            "chapter plan persistence",
            lambda chapter_plan=chapter_plan, chapter_no=chapter_no: save_text(
                get_chapter_plan_path(project_root, chapter_no),
                _render_chapter_plan_markdown(chapter_plan),
            ),
        )


def _to_chapter_index_entry(chapter_plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "chapter_no": chapter_plan["chapter_no"],
        "volume_no": chapter_plan["volume_no"],
        "title": chapter_plan["title"],
        "goal": chapter_plan["goal"],
        "status": chapter_plan["status"],
    }


def _render_outline_markdown(outline: dict[str, Any]) -> str:
    return "# 总纲\n\n```json\n" + json.dumps(outline, ensure_ascii=False, indent=2) + "\n```\n"


def _render_volumes_markdown(volume_plan: list[dict[str, Any]]) -> str:
    return "# 分卷规划\n\n```json\n" + json.dumps(volume_plan, ensure_ascii=False, indent=2) + "\n```\n"


def _render_chapter_plan_markdown(chapter_plan: dict[str, Any]) -> str:
    return "# 章节规划\n\n```json\n" + json.dumps(chapter_plan, ensure_ascii=False, indent=2) + "\n```\n"


def _load_outline_from_project(paths: dict[str, str]) -> dict[str, Any]:
    return _load_json_markdown_document(str(Path(paths["docs_dir"]) / "outline.md"), "Outline")


def _load_chapter_plan_from_project(project_root: str, chapter_no: int) -> dict[str, Any]:
    return _load_json_markdown_document(
        get_chapter_plan_path(project_root, chapter_no),
        "Chapter plan",
    )


def _load_json_markdown_document(path: str, document_name: str) -> dict[str, Any]:
    content = load_text(path)
    json_block = _extract_json_code_block(content)
    try:
        parsed = json.loads(json_block)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{document_name} document is not valid JSON: {exc.msg}") from exc

    if not isinstance(parsed, dict):
        raise ValueError(f"{document_name} document must contain a JSON object.")

    return parsed


def _extract_json_code_block(content: str) -> str:
    marker = "```json"
    start = content.find(marker)
    if start == -1:
        return content.strip()

    start += len(marker)
    end = content.find("```", start)
    if end == -1:
        return content[start:].strip()
    return content[start:end].strip()


def _load_chapter_index(paths: dict[str, str]) -> list[dict[str, Any]]:
    data = load_json(paths["chapters_json"])
    if not isinstance(data, dict):
        raise ValueError("Chapter index file must be a JSON object.")

    chapters = data.get("chapters")
    if not isinstance(chapters, list) or not all(isinstance(item, dict) for item in chapters):
        raise ValueError("Chapter index file must contain a 'chapters' array of objects.")

    return chapters


def _find_chapter_entry(chapters_index: list[dict[str, Any]], chapter_no: int) -> dict[str, Any]:
    for entry in chapters_index:
        if entry.get("chapter_no") == chapter_no:
            return entry
    raise ValueError(f"Chapter {chapter_no} was not found in chapters.json.")


def _load_previous_summary(project_root: str, chapter_no: int) -> str:
    if chapter_no <= 1:
        return ""

    previous_summary_path = get_chapter_summary_path(project_root, chapter_no - 1)
    if not Path(previous_summary_path).is_file():
        return ""

    return load_text(previous_summary_path).strip()


def _load_character_state(paths: dict[str, str]) -> list[Any]:
    data = load_json(paths["characters_json"])
    if isinstance(data, dict):
        characters = data.get("characters")
        if isinstance(characters, list):
            return characters
    return load_characters(paths["project_root"])


def _load_timeline_state(paths: dict[str, str]) -> list[Any]:
    data = load_json(paths["timeline_json"])
    if isinstance(data, dict):
        events = data.get("events")
        if isinstance(events, list):
            return events
    return load_timeline(paths["project_root"])


def _load_foreshadow_state(paths: dict[str, str]) -> list[Any]:
    data = load_json(paths["foreshadow_json"])
    if isinstance(data, dict):
        items = data.get("items")
        if isinstance(items, list):
            return items
    return load_foreshadows(paths["project_root"])


def _load_suggestion_for_commit(path: str, chapter_no: int) -> dict[str, Any]:
    data = load_json(path)
    if not isinstance(data, dict):
        raise ValueError("Suggestion file must contain a JSON object.")

    _validate_commit_suggestion(data)

    if data.get("chapter_no") != chapter_no:
        raise ValueError(
            f"Suggestion chapter_no mismatch: expected {chapter_no}, got {data.get('chapter_no')}."
        )

    if data.get("committed") is True:
        raise ValueError(f"Suggestion for chapter {chapter_no} has already been committed.")

    return data


def _validate_commit_suggestion(suggestion: dict[str, Any]) -> None:
    required_fields = (
        "chapter_no",
        "character_updates",
        "timeline_updates",
        "foreshadow_updates",
        "notes",
    )
    missing_fields = [field for field in required_fields if field not in suggestion]
    if missing_fields:
        missing = ", ".join(missing_fields)
        raise ValueError(f"Suggestion is missing required field(s): {missing}")

    _validate_commit_updates("character_updates", suggestion["character_updates"])
    _validate_commit_updates("timeline_updates", suggestion["timeline_updates"])
    _validate_commit_updates("foreshadow_updates", suggestion["foreshadow_updates"])


def _validate_commit_updates(field_name: str, updates: Any) -> None:
    if not isinstance(updates, list):
        raise ValueError(f"Suggestion field '{field_name}' must be a list.")

    for index, item in enumerate(updates, start=1):
        if not isinstance(item, dict):
            raise ValueError(
                f"Suggestion field '{field_name}' entry {index} must be a JSON object."
            )

        missing_fields = [
            field for field in ("action", "target", "content") if field not in item
        ]
        if missing_fields:
            missing = ", ".join(missing_fields)
            raise ValueError(
                f"Suggestion field '{field_name}' entry {index} is missing required field(s): {missing}"
            )


def _build_commit_result_from_suggestion(
    suggestion: dict[str, Any],
    chapter_no: int,
    suggestion_path: str,
) -> dict[str, Any]:
    return {
        "chapter_no": chapter_no,
        "suggestion_path": suggestion_path,
        "characters_updated": len(cast(list[Any], suggestion["character_updates"])),
        "timeline_updated": len(cast(list[Any], suggestion["timeline_updates"])),
        "foreshadow_updated": len(cast(list[Any], suggestion["foreshadow_updates"])),
    }


def _persist_prepared_formal_state(
    paths: dict[str, str],
    state_after: dict[str, dict[str, Any]],
) -> None:
    _run_stage(
        "character state persistence",
        lambda: save_json(paths["characters_json"], state_after["characters"]),
    )
    _run_stage(
        "timeline state persistence",
        lambda: save_json(paths["timeline_json"], state_after["timeline"]),
    )
    _run_stage(
        "foreshadow state persistence",
        lambda: save_json(paths["foreshadow_json"], state_after["foreshadow"]),
    )


def _load_state_payload_and_items(
    path: str,
    key: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    data = load_json(path)
    if not isinstance(data, dict):
        raise ValueError(f"State file {path} must contain a JSON object.")

    items = data.get(key)
    if not isinstance(items, list) or not all(isinstance(item, dict) for item in items):
        raise ValueError(f"State file {path} must contain a '{key}' array of objects.")

    return data, cast(list[dict[str, Any]], items)


def _load_state_container(path: str, key: str) -> list[dict[str, Any]]:
    data = load_json(path)
    if not isinstance(data, dict):
        raise ValueError(f"State file {path} must contain a JSON object.")

    items = data.get(key)
    if not isinstance(items, list) or not all(isinstance(item, dict) for item in items):
        raise ValueError(f"State file {path} must contain a '{key}' array of objects.")

    return cast(list[dict[str, Any]], items)


def _apply_character_updates(
    characters: list[dict[str, Any]],
    updates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    merged = [dict(character) for character in characters]

    for update in updates:
        target = str(update["target"])
        content = str(update["content"])
        character = _find_item_by_key(merged, "name", target)

        if character is None:
            character = {
                "name": target,
                "role": "unknown",
                "traits": [],
                "current_state": content,
            }
            merged.append(character)
            continue

        if update.get("action") == "update":
            existing_state = str(character.get("current_state", "")).strip()
            character["current_state"] = (
                f"{existing_state}\n{content}".strip() if existing_state else content
            )
        elif update.get("action") == "add" and not character.get("current_state"):
            character["current_state"] = content

    return merged


def _apply_timeline_updates(
    timeline: list[dict[str, Any]],
    updates: list[dict[str, Any]],
    chapter_no: int,
) -> list[dict[str, Any]]:
    merged = [dict(event) for event in timeline]

    for update in updates:
        merged.append(
            {
                "chapter_no": chapter_no,
                "event": str(update["content"]),
                "action": str(update["action"]),
                "target": str(update["target"]),
            }
        )

    return merged


def _apply_foreshadow_updates(
    foreshadow_items: list[dict[str, Any]],
    updates: list[dict[str, Any]],
    chapter_no: int,
) -> list[dict[str, Any]]:
    merged = [dict(item) for item in foreshadow_items]

    for update in updates:
        target = str(update["target"])
        content = str(update["content"])
        item = _find_item_by_key(merged, "id", target)

        if update.get("action") == "add":
            if item is None:
                merged.append(
                    {
                        "id": target,
                        "content": content,
                        "introduced_in": f"chapter_{chapter_no}",
                        "status": "open",
                    }
                )
            continue

        if item is None:
            merged.append(
                {
                    "id": target,
                    "content": content,
                    "introduced_in": f"chapter_{chapter_no}",
                    "status": content,
                }
            )
            continue

        item["status"] = content

    return merged


def _find_item_by_key(
    items: list[dict[str, Any]],
    key: str,
    value: str,
) -> dict[str, Any] | None:
    for item in items:
        if item.get(key) == value:
            return item
    return None


def _load_optional_module(module_name: str) -> ModuleType | None:
    try:
        return import_module(module_name)
    except ModuleNotFoundError as exc:
        if exc.name == module_name:
            return None
        raise
