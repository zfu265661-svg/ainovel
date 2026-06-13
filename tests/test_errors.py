"""Tests for shared exception definitions."""

from __future__ import annotations

import pytest

from core.chapter_service import ChapterServiceError
from core.checker_service import ConsistencyCheckParseError
from core.draft_service import DraftServiceError
from core.errors import ChapterPlanError
from core.errors import ConfigLoadError
from core.errors import ConsistencyCheckError
from core.errors import DraftGenerationError
from core.errors import LLMRequestError
from core.errors import NovelAgentError
from core.errors import OutlineGenerationError
from core.errors import PromptLoadError
from core.errors import RewriteError
from core.errors import StorageError
from core.errors import parse_json_with_repair
from core.llm_client import LLMClientError
from core.outline_service import OutlineParseError
from core.rewrite_service import RewriteServiceError
from core.workflow_service import WorkflowServiceError


ERROR_TYPES: tuple[type[NovelAgentError], ...] = (
    ConfigLoadError,
    PromptLoadError,
    LLMRequestError,
    OutlineGenerationError,
    ChapterPlanError,
    DraftGenerationError,
    ConsistencyCheckError,
    RewriteError,
    StorageError,
)


def test_base_error_can_be_instantiated() -> None:
    error = NovelAgentError("base error")

    assert str(error) == "base error"


def test_subclasses_inherit_from_base_error() -> None:
    for error_type in ERROR_TYPES:
        error = error_type("subclass error")

        assert isinstance(error, NovelAgentError)
        assert isinstance(error, Exception)


def test_error_message_is_preserved() -> None:
    error = StorageError("unable to save draft")

    assert str(error) == "unable to save draft"


def test_service_errors_inherit_from_shared_error_hierarchy() -> None:
    assert issubclass(LLMClientError, LLMRequestError)
    assert issubclass(OutlineParseError, OutlineGenerationError)
    assert issubclass(ChapterServiceError, ChapterPlanError)
    assert issubclass(DraftServiceError, DraftGenerationError)
    assert issubclass(ConsistencyCheckParseError, ConsistencyCheckError)
    assert issubclass(RewriteServiceError, RewriteError)
    assert issubclass(RewriteServiceError, ValueError)
    assert issubclass(WorkflowServiceError, NovelAgentError)


def test_parse_json_with_repair_accepts_plain_json() -> None:
    assert parse_json_with_repair('{"title": "Novel", "chapters": [1]}') == {
        "title": "Novel",
        "chapters": [1],
    }


def test_parse_json_with_repair_accepts_bom() -> None:
    assert parse_json_with_repair('\ufeff{"title": "Novel"}') == {"title": "Novel"}


def test_parse_json_with_repair_accepts_markdown_fence() -> None:
    assert parse_json_with_repair('```json\n{"title": "Novel"}\n```') == {
        "title": "Novel"
    }


def test_parse_json_with_repair_extracts_json_from_surrounding_text() -> None:
    response = 'Here is the JSON:\n{"title": "Novel"}\nDone.'

    assert parse_json_with_repair(response) == {"title": "Novel"}


def test_parse_json_with_repair_removes_control_chars_inside_strings() -> None:
    response = '{"title": "Broken\nTitle", "ok": true}'

    assert parse_json_with_repair(response) == {
        "title": "BrokenTitle",
        "ok": True,
    }


def test_parse_json_with_repair_reports_attempts_without_response_body() -> None:
    response = '{"title": "Broken"'

    with pytest.raises(ValueError) as exc_info:
        parse_json_with_repair(response)

    message = str(exc_info.value)
    assert "attempts=['strict', 'sanitized', 'extracted']" in message
    assert "original_error=JSONDecodeError" in message
    assert response not in message
