from __future__ import annotations

from unittest.mock import Mock

import pytest

from core.rewrite_service import RewriteServiceError, rewrite_text


def test_rewrite_text_returns_rewritten_string_with_json_braces_in_template(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    load_prompt_mock = Mock(
        return_value='Rewrite this JSON example:\n{"text": "绀轰緥"}\n\n{text}'
    )
    generate_text_mock = Mock(return_value="娑﹁壊鍚庣殑姝ｆ枃")
    llm_client_mock = Mock(return_value=Mock(generate_text=generate_text_mock))

    monkeypatch.setattr("core.rewrite_service.load_prompt", load_prompt_mock)
    monkeypatch.setattr("core.rewrite_service.LLMClient", llm_client_mock)

    result = rewrite_text("鍘熷姝ｆ枃")

    assert result == "娑﹁壊鍚庣殑姝ｆ枃"
    load_prompt_mock.assert_called_once_with("rewrite.txt")
    generate_text_mock.assert_called_once_with(
        'Rewrite this JSON example:\n{"text": "绀轰緥"}\n\n鍘熷姝ｆ枃'
    )


@pytest.mark.parametrize("text", ["", "   ", "\n\t"])
def test_rewrite_text_raises_on_empty_input(text: str) -> None:
    with pytest.raises(
        RewriteServiceError, match="Rewrite text cannot be empty or whitespace only"
    ):
        rewrite_text(text)


def test_rewrite_text_raises_on_empty_model_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "core.rewrite_service.load_prompt",
        Mock(return_value="Rewrite this:\n{text}"),
    )
    monkeypatch.setattr(
        "core.rewrite_service.LLMClient",
        Mock(return_value=Mock(generate_text=Mock(return_value="   "))),
    )

    with pytest.raises(RewriteServiceError, match="Rewrite model returned empty text"):
        rewrite_text("鍘熷姝ｆ枃")


def test_rewrite_text_wraps_llm_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "core.rewrite_service.load_prompt",
        Mock(return_value="Rewrite this:\n{text}"),
    )
    monkeypatch.setattr(
        "core.rewrite_service.LLMClient",
        Mock(return_value=Mock(generate_text=Mock(side_effect=RuntimeError("boom")))),
    )

    with pytest.raises(RewriteServiceError, match="Rewrite generation failed: boom"):
        rewrite_text("鍘熷姝ｆ枃")
