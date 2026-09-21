"""Model registry.

Adding a provider means writing one subclass and registering it here — the
Agent never changes. Future entries might be ``AnthropicModel``,
``GeminiModel`` or ``AzureOpenAIModel``.
"""

from __future__ import annotations

from agent_kit.config.loader import ModelSection
from agent_kit.model.base import (
    Message,
    Model,
    ModelError,
    ModelResponse,
    ToolCall,
    ToolSpec,
)
from agent_kit.model.mock import MOCK_REQUIREMENT_SUMMARY, MockModel
from agent_kit.model.openai import OpenAIModel

MODEL_REGISTRY: dict[str, type[Model]] = {
    MockModel.provider: MockModel,
    OpenAIModel.provider: OpenAIModel,
}


def available_providers() -> list[str]:
    return sorted(MODEL_REGISTRY)


def create_model(section: ModelSection) -> Model:
    """Instantiate the model described by a :class:`ModelSection`."""
    model_class = MODEL_REGISTRY.get(section.provider)
    if model_class is None:
        raise ModelError(
            f"Unknown model provider '{section.provider}'. "
            f"Available providers: {', '.join(available_providers())}."
        )
    return model_class(name=section.name, **section.options)


def required_env_vars(provider: str) -> tuple[str, ...]:
    """Environment variables a provider needs (empty for unknown providers)."""
    model_class = MODEL_REGISTRY.get(provider)
    return model_class.required_env_vars if model_class else ()


__all__ = [
    "MOCK_REQUIREMENT_SUMMARY",
    "MODEL_REGISTRY",
    "Message",
    "MockModel",
    "Model",
    "ModelError",
    "ModelResponse",
    "OpenAIModel",
    "ToolCall",
    "ToolSpec",
    "available_providers",
    "create_model",
    "required_env_vars",
]
