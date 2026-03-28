from __future__ import annotations

import sys
from typing import Any

import httpx
from openai import APIConnectionError, APITimeoutError, OpenAI

from config import Config, load_config
from core.errors import LLMRequestError


class LLMClientError(LLMRequestError):
    """Raised when text generation fails or returns an unusable payload."""


REQUEST_MAX_ATTEMPTS = 3
REQUEST_TIMEOUT_SECONDS = 60.0


class LLMClient:
    def __init__(self, config: Config | None = None) -> None:
        self.config = config or load_config()
        self._http_client = httpx.Client(
            http2=False,
            timeout=REQUEST_TIMEOUT_SECONDS,
            trust_env=False,
        )
        # The OpenAI SDK also works with OpenAI-compatible providers via base_url.
        self._client = OpenAI(
            api_key=self.config.openai_api_key,
            base_url=self.config.openai_base_url,
            http_client=self._http_client,
        )

    def generate_text(self, prompt: str) -> str:
        """Generate text from a prompt using a chat-completions compatible API."""
        return self.generate_text_with_context(prompt)

    def generate_text_with_context(
        self,
        prompt: str,
        stage_name: str | None = None,
        volume_no: int | None = None,
    ) -> str:
        """Generate text with optional stage context for debug tracing."""
        prompt_chars = len(prompt)
        _emit_request_log(
            status="start",
            stage_name=stage_name,
            volume_no=volume_no,
            prompt_chars=prompt_chars,
        )
        last_error: Exception | None = None

        for attempt in range(1, REQUEST_MAX_ATTEMPTS + 1):
            try:
                response = self._client.chat.completions.create(
                    model=self.config.model_name,
                    messages=[{"role": "user", "content": prompt}],
                    stream=False,
                )
                break
            except Exception as exc:
                last_error = exc
                _emit_request_log(
                    status="failure",
                    stage_name=stage_name,
                    volume_no=volume_no,
                    prompt_chars=prompt_chars,
                    detail=f"attempt={attempt} error={exc.__class__.__name__}",
                )
                if attempt >= REQUEST_MAX_ATTEMPTS or not _is_retryable_request_error(exc):
                    raise LLMClientError(
                        _format_request_error(
                            exc,
                            attempt,
                            stage_name=stage_name,
                            volume_no=volume_no,
                        )
                    ) from exc
        else:
            if last_error is not None:
                raise LLMClientError(
                    _format_request_error(
                        last_error,
                        REQUEST_MAX_ATTEMPTS,
                        stage_name=stage_name,
                        volume_no=volume_no,
                    )
                ) from last_error
            raise LLMClientError("LLM request failed: unknown request error.")

        content = self._extract_text(response)
        if not content:
            raise LLMClientError("LLM response did not include any text content.")

        _emit_request_log(
            status="success",
            stage_name=stage_name,
            volume_no=volume_no,
            prompt_chars=prompt_chars,
        )
        return content

    def _extract_text(self, response: Any) -> str:
        choices = getattr(response, "choices", None)
        if not choices:
            return ""

        first_choice = choices[0]
        message = getattr(first_choice, "message", None)
        if message is None:
            return ""

        content = getattr(message, "content", "")
        if isinstance(content, str):
            return content.strip()

        if isinstance(content, list):
            text_parts: list[str] = []
            for item in content:
                if isinstance(item, dict):
                    text = item.get("text")
                    if isinstance(text, str) and text.strip():
                        text_parts.append(text.strip())
                else:
                    text = getattr(item, "text", None)
                    if isinstance(text, str) and text.strip():
                        text_parts.append(text.strip())
            return "\n".join(text_parts).strip()

        return ""


def _is_retryable_request_error(exc: Exception) -> bool:
    return isinstance(exc, (APIConnectionError, APITimeoutError))


def _format_request_error(
    exc: Exception,
    attempt: int,
    stage_name: str | None = None,
    volume_no: int | None = None,
) -> str:
    message = (
        f"{_format_context_prefix(stage_name=stage_name, volume_no=volume_no)}"
        f"LLM request failed after attempt {attempt} ({exc.__class__.__name__}): {exc}"
    )

    cause = exc.__cause__
    if cause is not None:
        message += f" | cause: {cause.__class__.__name__}: {cause}"

    return message


def _emit_request_log(
    status: str,
    prompt_chars: int,
    stage_name: str | None = None,
    volume_no: int | None = None,
    detail: str | None = None,
) -> None:
    parts = [
        "[LLM]",
        _format_context_prefix(stage_name=stage_name, volume_no=volume_no).strip(),
        f"status={status}",
        f"prompt_chars={prompt_chars}",
    ]
    if detail:
        parts.append(detail)
    print(" ".join(part for part in parts if part), file=sys.stderr)


def _format_context_prefix(
    stage_name: str | None = None,
    volume_no: int | None = None,
) -> str:
    parts: list[str] = []
    if stage_name:
        parts.append(f"stage={stage_name}")
    if volume_no is not None:
        parts.append(f"volume_no={volume_no}")
    return " ".join(parts)
