"""Unit tests for the model abstraction and its implementations."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from agent_kit.config import ModelSection
from agent_kit.model import (
    MOCK_REQUIREMENT_SUMMARY,
    MODEL_REGISTRY,
    MockModel,
    ModelError,
    OpenAIModel,
    available_providers,
    create_model,
    required_env_vars,
)
from agent_kit.model.base import Message, ModelResponse, ToolCall, ToolSpec
from agent_kit.model.openai import to_openai_message


# --- MockModel ------------------------------------------------------------
def test_mock_model_is_deterministic() -> None:
    model = MockModel()
    first = model.generate([Message.user("anything")])
    second = model.generate([Message.user("something else")])
    assert first.content == second.content == MOCK_REQUIREMENT_SUMMARY


def test_mock_model_returns_every_required_section() -> None:
    from agent_kit.evaluation import REQUIRED_SECTIONS, find_missing_sections

    assert find_missing_sections(MOCK_REQUIREMENT_SUMMARY, REQUIRED_SECTIONS) == []


def test_mock_model_script_is_replayed_and_clamped() -> None:
    script = [
        ModelResponse(content=None, tool_calls=[ToolCall(id="1", name="filesystem")]),
        ModelResponse(content="final"),
    ]
    model = MockModel(script=script)

    assert model.generate([]).tool_calls[0].name == "filesystem"
    assert model.generate([]).content == "final"
    assert model.generate([]).content == "final"  # last response repeats


def test_mock_model_records_prompts() -> None:
    model = MockModel()
    model.generate([Message.system("sys"), Message.user("hi")])
    assert model.invocation_count == 1
    assert model.calls[0][1].content == "hi"


# --- registry -------------------------------------------------------------
def test_registry_exposes_both_providers() -> None:
    assert available_providers() == ["mock", "openai"]
    assert set(MODEL_REGISTRY) == {"mock", "openai"}


def test_create_model_builds_mock_from_configuration() -> None:
    model = create_model(ModelSection(provider="mock", name="mock-model"))
    assert isinstance(model, MockModel)
    assert model.describe() == "mock/mock-model"


def test_create_model_rejects_unknown_provider() -> None:
    with pytest.raises(ModelError, match="Unknown model provider"):
        create_model(ModelSection(provider="nope", name="x"))


def test_required_env_vars_per_provider() -> None:
    assert required_env_vars("openai") == ("OPENAI_API_KEY",)
    assert required_env_vars("mock") == ()
    assert required_env_vars("unknown") == ()


# --- OpenAIModel ----------------------------------------------------------
def test_openai_model_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ModelError, match="OPENAI_API_KEY is not set"):
        OpenAIModel("gpt-4o-mini")


def test_openai_message_conversion_for_tool_results() -> None:
    message = Message.tool_result(tool_call_id="call_1", name="filesystem", content="hello")
    assert to_openai_message(message) == {
        "role": "tool",
        "tool_call_id": "call_1",
        "content": "hello",
    }


def test_openai_message_conversion_for_tool_calls() -> None:
    message = Message.assistant(
        None,
        tool_calls=[ToolCall(id="call_1", name="filesystem", arguments={"action": "read_file"})],
    )
    payload = to_openai_message(message)
    assert payload["tool_calls"][0]["function"]["name"] == "filesystem"
    assert payload["tool_calls"][0]["function"]["arguments"] == '{"action": "read_file"}'


def test_openai_model_maps_tool_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    model = OpenAIModel("gpt-test")

    captured: dict[str, object] = {}

    class FakeCompletions:
        def create(self, **kwargs):
            captured.update(kwargs)
            message = SimpleNamespace(
                content=None,
                tool_calls=[
                    SimpleNamespace(
                        id="call_1",
                        function=SimpleNamespace(
                            name="filesystem",
                            arguments='{"action": "read_file", "path": "a.txt"}',
                        ),
                    )
                ],
            )
            return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    model._client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))

    response = model.generate(
        [Message.user("read a.txt")],
        [ToolSpec(name="filesystem", description="fs", parameters={"type": "object"})],
    )

    assert response.tool_calls[0].arguments == {"action": "read_file", "path": "a.txt"}
    assert captured["model"] == "gpt-test"
    assert captured["tools"][0]["function"]["name"] == "filesystem"


def test_openai_model_uses_base_url_option(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    model = OpenAIModel("gpt-test", base_url="http://localhost:11434/v1")
    assert model.base_url == "http://localhost:11434/v1"
