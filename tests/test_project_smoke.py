from __future__ import annotations

import importlib
import importlib.util


def test_key_modules_can_be_imported() -> None:
    required_modules = [
        "config",
        "core.prompt_loader",
        "core.llm_client",
        "core.outline_service",
        "core.chapter_service",
        "core.draft_service",
    ]
    optional_modules = [
        "core.workflow_service",
        "core.rewrite_service",
        "core.storage",
        "core.checker_service",
        "core.character_service",
        "core.export_service",
        "core.foreshadow_service",
        "core.summarizer",
        "core.timeline_service",
    ]

    for module_name in required_modules:
        module = importlib.import_module(module_name)
        assert module is not None, f"Failed to import required module: {module_name}"

    for module_name in optional_modules:
        if importlib.util.find_spec(module_name) is None:
            continue
        module = importlib.import_module(module_name)
        assert module is not None, f"Failed to import optional module: {module_name}"
