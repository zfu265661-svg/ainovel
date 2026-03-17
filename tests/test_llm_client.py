from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from config import Config
from core.llm_client import LLMClient, LLMClientError


def test_generate_text_returns_string(monkeypatch: pytest.MonkeyPatch) -> None:
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="generated text"))]
    )
    create_mock = Mock(return_value=response)
    openai_mock = Mock(
        return_value=SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=create_mock))
        )
    )
    monkeypatch.setattr("core.llm_client.OpenAI", openai_mock)

    client = LLMClient(
        Config(
            openai_api_key="test-key",
            openai_base_url="https://example.com/v1",
            model_name="test-model",
        )
    )

    result = client.generate_text("hello")

    assert result == "generated text"
    openai_mock.assert_called_once_with(
        api_key="test-key",
        base_url="https://example.com/v1",
    )
    create_mock.assert_called_once_with(
        model="test-model",
        messages=[{"role": "user", "content": "hello"}],
    )


def test_generate_text_uses_custom_provider_base_url_and_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="deepseek text"))]
    )
    create_mock = Mock(return_value=response)
    openai_mock = Mock(
        return_value=SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=create_mock))
        )
    )
    monkeypatch.setattr("core.llm_client.OpenAI", openai_mock)

    client = LLMClient(
        Config(
            openai_api_key="deepseek-key",
            openai_base_url="https://api.deepseek.com",
            model_name="deepseek-chat",
        )
    )

    result = client.generate_text("hello")

    assert result == "deepseek text"
    openai_mock.assert_called_once_with(
        api_key="deepseek-key",
        base_url="https://api.deepseek.com",
    )
    create_mock.assert_called_once_with(
        model="deepseek-chat",
        messages=[{"role": "user", "content": "hello"}],
    )


def test_generate_text_wraps_api_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    create_mock = Mock(side_effect=Exception("upstream failure"))
    openai_mock = Mock(
        return_value=SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=create_mock))
        )
    )
    monkeypatch.setattr("core.llm_client.OpenAI", openai_mock)

    client = LLMClient(
        Config(
            openai_api_key="test-key",
            openai_base_url="https://example.com/v1",
            model_name="test-model",
        )
    )

    with pytest.raises(LLMClientError, match="LLM request failed: upstream failure"):
        client.generate_text("hello")


def test_generate_text_raises_on_empty_response(monkeypatch: pytest.MonkeyPatch) -> None:
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="   "))]
    )
    create_mock = Mock(return_value=response)
    openai_mock = Mock(
        return_value=SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=create_mock))
        )
    )
    monkeypatch.setattr("core.llm_client.OpenAI", openai_mock)

    client = LLMClient(
        Config(
            openai_api_key="test-key",
            openai_base_url="https://example.com/v1",
            model_name="test-model",
        )
    )

    with pytest.raises(LLMClientError, match="did not include any text content"):
        client.generate_text("hello")
