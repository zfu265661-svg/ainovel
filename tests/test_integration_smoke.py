import importlib
import importlib.util


def test_main_modules_can_be_imported() -> None:
    required_modules = [
        "config",
        "core.prompt_loader",
        "core.llm_client",
    ]
    optional_modules = [
        "core.outline_service",
        "core.chapter_service",
        "core.draft_service",
        "core.checker_service",
        "core.storage",
    ]

    for module_name in required_modules:
        importlib.import_module(module_name)

    for module_name in optional_modules:
        if importlib.util.find_spec(module_name) is not None:
            importlib.import_module(module_name)
