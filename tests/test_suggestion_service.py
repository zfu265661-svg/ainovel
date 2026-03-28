from __future__ import annotations

import json

import pytest

from core.suggestion_service import SuggestionParseError, generate_state_suggestions


def test_generate_state_suggestions_returns_parsed_dict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompt_template = (
        "chapter={chapter_no}\n"
        "outline={outline}\n"
        "plan={chapter_plan}\n"
        "rewrite={rewritten_text}\n"
        "summary={chapter_summary}\n"
        "characters={characters}\n"
        "timeline={timeline}\n"
        "foreshadow={foreshadow}"
    )
    response_payload = {
        "chapter_no": 3,
        "character_updates": [
            {
                "action": "update",
                "target": "Lin Yue",
                "content": "Trust in the sect keeps falling.",
            }
        ],
        "timeline_updates": [
            {
                "action": "add",
                "target": "chapter_3",
                "content": "Lin Yue discovers the hidden gate in the old vault.",
            }
        ],
        "foreshadow_updates": [
            {
                "action": "add",
                "target": "jade_pendant",
                "content": "The jade pendant reacts to the stone gate.",
            }
        ],
        "notes": "These are suggestions only and still need explicit review.",
    }

    monkeypatch.setattr("core.suggestion_service.load_prompt", lambda name: prompt_template)

    class FakeLLMClient:
        def generate_text_with_context(
            self,
            prompt: str,
            stage_name: str | None = None,
            volume_no: int | None = None,
        ) -> str:
            assert "chapter=3" in prompt
            assert '"title": "Test Outline"' in prompt
            assert "rewritten chapter body" in prompt
            assert "chapter summary text" in prompt
            assert stage_name == "state suggestion generation"
            return json.dumps(response_payload, ensure_ascii=False)

    monkeypatch.setattr("core.suggestion_service.LLMClient", FakeLLMClient)

    result = generate_state_suggestions(
        chapter_no=3,
        outline={"title": "Test Outline"},
        chapter_plan={"chapter_no": 3, "title": "Chapter Three"},
        rewritten_text="rewritten chapter body",
        chapter_summary="chapter summary text",
        characters=[{"name": "Lin Yue"}],
        timeline=[{"chapter_no": 2, "event": "Previous chapter event"}],
        foreshadow=[{"id": "fs-1", "content": "Older clue"}],
    )

    assert result == response_payload


def test_generate_state_suggestions_raises_for_empty_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("core.suggestion_service.load_prompt", lambda name: "prompt")

    class FakeLLMClient:
        def generate_text_with_context(
            self,
            prompt: str,
            stage_name: str | None = None,
            volume_no: int | None = None,
        ) -> str:
            return "   "

    monkeypatch.setattr("core.suggestion_service.LLMClient", FakeLLMClient)

    with pytest.raises(SuggestionParseError, match="State suggestion response is empty"):
        generate_state_suggestions(1, {}, {}, "body", "summary", [], [], [])


def test_generate_state_suggestions_raises_for_invalid_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("core.suggestion_service.load_prompt", lambda name: "prompt")

    class FakeLLMClient:
        def generate_text_with_context(
            self,
            prompt: str,
            stage_name: str | None = None,
            volume_no: int | None = None,
        ) -> str:
            return "not json"

    monkeypatch.setattr("core.suggestion_service.LLMClient", FakeLLMClient)

    with pytest.raises(SuggestionParseError, match="not valid JSON|response_snippet"):
        generate_state_suggestions(1, {}, {}, "body", "summary", [], [], [])


def test_generate_state_suggestions_raises_for_missing_required_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("core.suggestion_service.load_prompt", lambda name: "prompt")

    class FakeLLMClient:
        def generate_text_with_context(
            self,
            prompt: str,
            stage_name: str | None = None,
            volume_no: int | None = None,
        ) -> str:
            return json.dumps(
                {
                    "chapter_no": 1,
                    "character_updates": [],
                    "timeline_updates": [],
                    "notes": "Missing foreshadow_updates",
                },
                ensure_ascii=False,
            )

    monkeypatch.setattr("core.suggestion_service.LLMClient", FakeLLMClient)

    with pytest.raises(
        SuggestionParseError,
        match="missing required field\\(s\\): foreshadow_updates",
    ):
        generate_state_suggestions(1, {}, {}, "body", "summary", [], [], [])


def test_generate_state_suggestions_parses_json_code_block_and_normalizes_rich_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("core.suggestion_service.load_prompt", lambda name: "prompt")

    class FakeLLMClient:
        def generate_text_with_context(
            self,
            prompt: str,
            stage_name: str | None = None,
            volume_no: int | None = None,
        ) -> str:
            return """```json
{
  "chapter_no": 1,
  "character_updates": [
    {
      "character_name": "Lin Jin",
      "update_fields": {
        "physical_state": "heavily injured",
        "mental_state": "survival mode"
      },
      "reason": "opening chapter shift"
    }
  ],
  "timeline_updates": [
    {
      "event": "prison bone extraction",
      "time_anchor": "opening",
      "description": "Lin Jin had his supreme bone ripped away.",
      "impact": "The protagonist falls to rock bottom."
    }
  ],
  "foreshadow_updates": [
    {
      "foreshadow_content": "black bone hunger instinct",
      "related_to": "protagonist ability",
      "details": "The black bone starts devouring ambient energy.",
      "potential_payoff": "future growth"
    }
  ],
  "notes": "Suggestions only."
}
```"""

    monkeypatch.setattr("core.suggestion_service.LLMClient", FakeLLMClient)

    result = generate_state_suggestions(1, {}, {}, "body", "summary", [], [], [])

    assert result == {
        "chapter_no": 1,
        "character_updates": [
            {
                "action": "update",
                "target": "Lin Jin",
                "content": "physical_state: heavily injured\nmental_state: survival mode",
            }
        ],
        "timeline_updates": [
            {
                "action": "add",
                "target": "prison bone extraction",
                "content": "Lin Jin had his supreme bone ripped away.\n影响: The protagonist falls to rock bottom.",
            }
        ],
        "foreshadow_updates": [
            {
                "action": "add",
                "target": "black_bone_hunger_instinct",
                "content": "black bone hunger instinct\nThe black bone starts devouring ambient energy.",
            }
        ],
        "notes": "Suggestions only.",
    }


def test_generate_state_suggestions_unwraps_nested_payload_with_required_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("core.suggestion_service.load_prompt", lambda name: "prompt")

    class FakeLLMClient:
        def generate_text_with_context(
            self,
            prompt: str,
            stage_name: str | None = None,
            volume_no: int | None = None,
        ) -> str:
            return json.dumps(
                {
                    "result": {
                        "chapter_no": 2,
                        "character_updates": [],
                        "timeline_updates": [
                            {
                                "action": "add",
                                "target": "chapter_2",
                                "content": "Second chapter event",
                            }
                        ],
                        "foreshadow_updates": [],
                        "notes": "Nested payload.",
                    }
                },
                ensure_ascii=False,
            )

    monkeypatch.setattr("core.suggestion_service.LLMClient", FakeLLMClient)

    result = generate_state_suggestions(2, {}, {}, "body", "summary", [], [], [])

    assert result == {
        "chapter_no": 2,
        "character_updates": [],
        "timeline_updates": [
            {
                "action": "add",
                "target": "chapter_2",
                "content": "Second chapter event",
            }
        ],
        "foreshadow_updates": [],
        "notes": "Nested payload.",
    }
