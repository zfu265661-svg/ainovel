"""Tests for shared exception definitions."""

from __future__ import annotations

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
