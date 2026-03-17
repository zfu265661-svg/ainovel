from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


DEFAULT_OPENAI_COMPAT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_OPENAI_BASE_URL = DEFAULT_OPENAI_COMPAT_BASE_URL


class ConfigError(ValueError):
    """Raised when required runtime configuration is missing or invalid."""


@dataclass(frozen=True)
class Config:
    openai_api_key: str
    openai_base_url: str
    model_name: str


def load_config() -> Config:
    """Load OpenAI-compatible provider settings from environment variables."""
    load_dotenv(override=False)

    openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not openai_api_key:
        raise ConfigError("Missing OPENAI_API_KEY: please set the API key for your provider.")

    model_name = os.getenv("MODEL_NAME", "").strip()
    if not model_name:
        raise ConfigError("Missing MODEL_NAME: please set the model name for your provider.")

    openai_base_url = (
        os.getenv("OPENAI_BASE_URL", "").strip() or DEFAULT_OPENAI_COMPAT_BASE_URL
    )

    return Config(
        openai_api_key=openai_api_key,
        openai_base_url=openai_base_url,
        model_name=model_name,
    )
