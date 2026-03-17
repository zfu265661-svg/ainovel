from __future__ import annotations

from typing import Any

from openai import OpenAI

from config import Config, load_config
from core.errors import LLMRequestError


class LLMClientError(LLMRequestError):
    """Raised when text generation fails or returns an unusable payload."""


class LLMClient:
    def __init__(self, config: Config | None = None) -> None:
        self.config = config or load_config()
        # The OpenAI SDK also works with OpenAI-compatible providers via base_url.
        self._client = OpenAI(
            api_key=self.config.openai_api_key,
            base_url=self.config.openai_base_url,
        )

    def generate_text(self, prompt: str) -> str:
        """Generate text from a prompt using a chat-completions compatible API."""
        try:
            response = self._client.chat.completions.create(
                model=self.config.model_name,
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as exc:
            raise LLMClientError(f"LLM request failed: {exc}") from exc

        content = self._extract_text(response)
        if not content:
            raise LLMClientError("LLM response did not include any text content.")

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
