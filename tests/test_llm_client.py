from types import SimpleNamespace
from unittest.mock import ANY, Mock

import httpx
from openai import APIConnectionError
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
        http_client=ANY,
    )
    assert isinstance(openai_mock.call_args.kwargs["http_client"], httpx.Client)
    create_mock.assert_called_once_with(
        model="test-model",
        messages=[{"role": "user", "content": "hello"}],
        stream=False,
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
            model_name="deepseek-v4-flash",
        )
    )

    result = client.generate_text("hello")

    assert result == "deepseek text"
    openai_mock.assert_called_once_with(
        api_key="deepseek-key",
        base_url="https://api.deepseek.com",
        http_client=ANY,
    )
    assert isinstance(openai_mock.call_args.kwargs["http_client"], httpx.Client)
    create_mock.assert_called_once_with(
        model="deepseek-v4-flash",
        messages=[{"role": "user", "content": "hello"}],
        stream=False,
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

    with pytest.raises(
        LLMClientError,
        match=r"LLM request failed after attempt 1 \(Exception\): upstream failure",
    ):
        client.generate_text("hello")


def test_generate_text_retries_connection_errors_before_succeeding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="generated after retry"))]
    )
    request = httpx.Request("POST", "https://api.deepseek.com/chat/completions")
    create_mock = Mock(
        side_effect=[
            APIConnectionError(message="Connection error.", request=request),
            response,
        ]
    )
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
            model_name="deepseek-v4-flash",
        )
    )

    result = client.generate_text("hello")

    assert result == "generated after retry"
    assert create_mock.call_count == 2


def test_generate_text_includes_exception_type_and_root_cause_for_connection_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = httpx.Request("POST", "https://api.deepseek.com/chat/completions")
    create_mock = Mock()

    def raise_error(*args, **kwargs):
        error = APIConnectionError(message="Connection error.", request=request)
        error.__cause__ = RuntimeError("socket closed")
        raise error

    create_mock.side_effect = raise_error
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
            model_name="deepseek-v4-flash",
        )
    )

    with pytest.raises(
        LLMClientError,
        match=r"APIConnectionError.*Connection error\..*cause: RuntimeError: socket closed",
    ):
        client.generate_text("hello")


def test_generate_text_with_context_logs_stage_and_prompt_size(
    monkeypatch: pytest.MonkeyPatch,
    capsys,
) -> None:
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

    result = client.generate_text_with_context(
        "hello",
        stage_name="chapter planning",
        volume_no=2,
    )

    captured = capsys.readouterr()
    assert result == "generated text"
    assert "[LLM] stage=chapter planning volume_no=2 status=start prompt_chars=5" in captured.err
    assert "[LLM] stage=chapter planning volume_no=2 status=success prompt_chars=5" in captured.err


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
