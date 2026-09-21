"""OpenAI provider — the only module allowed to know the OpenAI SDK."""

from __future__ import annotations

import json
import os
from typing import Any

from agent_kit.model.base import (
    Message,
    Model,
    ModelError,
    ModelResponse,
    ToolCall,
    ToolSpec,
)

API_KEY_ENV_VAR = "OPENAI_API_KEY"


def to_openai_message(message: Message) -> dict[str, Any]:
    """Convert a :class:`Message` into the OpenAI chat-completions shape."""
    if message.role == "tool":
        return {
            "role": "tool",
            "tool_call_id": message.tool_call_id,
            "content": message.content or "",
        }

    payload: dict[str, Any] = {"role": message.role}
    payload["content"] = message.content or ""
    if message.tool_calls:
        payload["tool_calls"] = [
            {
                "id": call.id,
                "type": "function",
                "function": {"name": call.name, "arguments": json.dumps(call.arguments)},
            }
            for call in message.tool_calls
        ]
    return payload


def to_openai_tool(spec: ToolSpec) -> dict[str, Any]:
    """Convert a :class:`ToolSpec` into an OpenAI function tool definition."""
    return {
        "type": "function",
        "function": {
            "name": spec.name,
            "description": spec.description,
            "parameters": spec.parameters,
        },
    }


class OpenAIModel(Model):
    """Chat-completions backed model with tool calling.

    The SDK is imported lazily so importing :mod:`agent_kit` never requires the
    optional ``openai`` extra.
    """

    provider = "openai"
    required_env_vars: tuple[str, ...] = (API_KEY_ENV_VAR,)

    def __init__(
        self,
        name: str,
        api_key: str | None = None,
        base_url: str | None = None,
        **options: Any,
    ) -> None:
        super().__init__(name, **options)
        self.api_key = api_key or os.environ.get(API_KEY_ENV_VAR)
        if not self.api_key:
            raise ModelError(
                f"{API_KEY_ENV_VAR} is not set. Export it (see .env.example) "
                "or set model.provider to 'mock' in .agent/config.yaml."
            )
        self.base_url = base_url or os.environ.get("OPENAI_BASE_URL")
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                from openai import OpenAI  # imported lazily on first call
            except ImportError as exc:  # pragma: no cover - depends on environment
                raise ModelError(
                    "The optional 'openai' package is not installed. Install it with "
                    "uv tool install 'agent-kit-poc[openai]' --force (or "
                    "uv sync --all-extras for development)."
                ) from exc
            self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        return self._client

    def generate(
        self,
        messages: list[Message],
        tools: list[ToolSpec] | None = None,
    ) -> ModelResponse:
        client = self._get_client()
        request: dict[str, Any] = {
            "model": self.name,
            "messages": [to_openai_message(message) for message in messages],
        }
        if tools:
            request["tools"] = [to_openai_tool(spec) for spec in tools]
        # Pass through any extra configuration keys (temperature, max_tokens, ...).
        request.update(self.options)

        try:
            completion = client.chat.completions.create(**request)
        except Exception as exc:  # pragma: no cover - network path
            raise ModelError(f"OpenAI request failed: {exc}") from exc

        message = completion.choices[0].message
        tool_calls: list[ToolCall] = []
        for call in message.tool_calls or []:
            raw_arguments = call.function.arguments or "{}"
            try:
                arguments = json.loads(raw_arguments)
            except json.JSONDecodeError:
                arguments = {"_raw": raw_arguments}
            tool_calls.append(ToolCall(id=call.id, name=call.function.name, arguments=arguments))

        return ModelResponse(content=message.content, tool_calls=tool_calls)
