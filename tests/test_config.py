import pytest

import config
from config import (
    Config,
    ConfigError,
    DEFAULT_OPENAI_BASE_URL,
    DEFAULT_OPENAI_COMPAT_BASE_URL,
    load_config,
)


@pytest.fixture(autouse=True)
def disable_dotenv_loading(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "load_dotenv", lambda override=False: None)


def test_load_config_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.com/v1")
    monkeypatch.setenv("MODEL_NAME", "test-model")

    config = load_config()

    assert config == Config(
        openai_api_key="test-key",
        openai_base_url="https://example.com/v1",
        model_name="test-model",
    )


def test_load_config_raises_when_api_key_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("MODEL_NAME", "test-model")

    with pytest.raises(ConfigError, match="API key for your provider"):
        load_config()


def test_load_config_raises_when_model_name_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.delenv("MODEL_NAME", raising=False)

    with pytest.raises(ConfigError, match="model name for your provider"):
        load_config()


def test_load_config_uses_default_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("MODEL_NAME", "test-model")
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)

    config = load_config()

    assert config.openai_base_url == DEFAULT_OPENAI_BASE_URL
    assert config.openai_base_url == DEFAULT_OPENAI_COMPAT_BASE_URL


def test_load_config_accepts_non_openai_compatible_base_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "deepseek-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.deepseek.com")
    monkeypatch.setenv("MODEL_NAME", "deepseek-v4-flash")

    config = load_config()

    assert config == Config(
        openai_api_key="deepseek-key",
        openai_base_url="https://api.deepseek.com",
        model_name="deepseek-v4-flash",
    )
