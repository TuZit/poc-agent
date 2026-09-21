"""The agent loop.

    Input + system instructions + skill + tools + model
        ↓
    Call model ──► tool calls? ── yes ──► execute tools ──► feed results back
                        │
                        no
                        ↓
                   final output

Deliberately small: no planner, no memory store, no orchestration engine. The
dependency direction is ``Agent -> {Model, Tool, Skill}`` interfaces only, so
the runtime never imports a provider SDK.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from agent_kit.agent.state import AgentState, ToolInvocation
from agent_kit.model.base import Message, Model, ModelResponse, ToolCall
from agent_kit.skills.base import Skill
from agent_kit.tools.base import Tool, ToolError, ToolResult

DEFAULT_MAX_ITERATIONS = 8

BASE_SYSTEM_PROMPT = (
    "You are {agent_name}, a focused software engineering agent from the Agent Kit POC. "
    "Follow the loaded skill instructions exactly. Use the available tools when they help, "
    "and finish with the final answer as Markdown — do not ask follow-up questions."
)


class AgentError(Exception):
    """Raised when the agent loop cannot produce a final answer."""


@dataclass(frozen=True)
class AgentResult:
    """Result of one agent run."""

    output: str
    state: AgentState

    @property
    def tool_invocations(self) -> list[ToolInvocation]:
        return self.state.tool_invocations

    @property
    def tool_call_count(self) -> int:
        return len(self.state.tool_invocations)

    @property
    def iterations(self) -> int:
        return self.state.iterations


class Agent:
    """Minimal tool-using agent."""

    def __init__(
        self,
        model: Model,
        tools: Iterable[Tool] | None = None,
        system_prompt: str | None = None,
        max_iterations: int = DEFAULT_MAX_ITERATIONS,
    ) -> None:
        self.model = model
        self.tools: dict[str, Tool] = {tool.name: tool for tool in (tools or [])}
        self.system_prompt = system_prompt or BASE_SYSTEM_PROMPT.format(agent_name="agent-kit")
        self.max_iterations = max(1, int(max_iterations))

    # -- context -----------------------------------------------------------
    def build_system_message(self, skill: Skill | None = None) -> Message:
        """System instructions = base prompt + loaded skill + tool inventory."""
        parts = [self.system_prompt]
        if skill is not None:
            parts.append(f"# Loaded skill: {skill.name}\n\n{skill.instructions}")
        if self.tools:
            parts.append("Available tools: " + ", ".join(sorted(self.tools)) + ".")
        return Message.system("\n\n".join(parts))

    def tool_specs(self) -> list:
        return [tool.spec() for tool in self.tools.values()]

    # -- execution ---------------------------------------------------------
    def run(self, user_input: str, skill: Skill | None = None) -> AgentResult:
        """Run the model/tool loop until the model stops calling tools."""
        state = AgentState()
        state.add(self.build_system_message(skill))
        state.add(Message.user(user_input))
        specs = self.tool_specs() or None

        while state.iterations < self.max_iterations:
            state.iterations += 1
            response: ModelResponse = self.model.generate(state.messages, specs)

            if not response.wants_tool_call:
                output = (response.content or "").strip()
                state.add(Message.assistant(output))
                state.final_output = output
                state.finished = True
                return AgentResult(output=output, state=state)

            # Assistant turn that asks for tools, then one tool message per call.
            state.add(Message.assistant(response.content, tool_calls=response.tool_calls))
            for call in response.tool_calls:
                result = self.execute_tool(call)
                state.record_tool(
                    ToolInvocation(
                        tool=call.name,
                        arguments=dict(call.arguments),
                        success=result.success,
                        output=result.output,
                    )
                )
                state.add(
                    Message.tool_result(
                        tool_call_id=call.id,
                        name=call.name,
                        content=result.output,
                    )
                )

        raise AgentError(
            f"Agent did not produce a final answer within {self.max_iterations} iterations."
        )

    def execute_tool(self, call: ToolCall) -> ToolResult:
        """Execute one tool call, converting any failure into a tool result."""
        tool = self.tools.get(call.name)
        if tool is None:
            available = ", ".join(sorted(self.tools)) or "(none)"
            return ToolResult(
                success=False,
                output=f"Unknown tool '{call.name}'. Available tools: {available}.",
            )
        try:
            return tool.execute(**call.arguments)
        except ToolError as exc:
            return ToolResult(success=False, output=str(exc))
        except TypeError as exc:
            return ToolResult(
                success=False,
                output=f"Invalid arguments for tool '{call.name}': {exc}",
            )
        except OSError as exc:
            return ToolResult(success=False, output=f"Tool '{call.name}' failed: {exc}")
