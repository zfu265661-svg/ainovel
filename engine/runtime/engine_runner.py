from __future__ import annotations

from engine.pipeline.chapter_pipeline import ChapterPipeline
from infrastructure.llm.client import DeterministicLLMClient
from infrastructure.persistence.json_repository import JsonProjectRepository


def build_default_pipeline(repository: JsonProjectRepository | None = None) -> ChapterPipeline:
    return ChapterPipeline(
        repository=repository or JsonProjectRepository(),
        llm_client=DeterministicLLMClient(),
    )
