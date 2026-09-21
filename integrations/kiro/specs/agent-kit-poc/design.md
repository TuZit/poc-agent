# Design Document — Agent Kit POC workspace

## Overview

Agent Kit POC is one installable Python package that provides a layered runtime and
a thin CLI. Configuration lives in `.agent/config.yaml`; prompt instructions live in
Markdown skills; models, tools and workflows are pluggable behind small interfaces.
Kiro reaches the same runtime through an MCP stdio server, and the workspace ships
steering, hooks, prompts and spec artifacts that point at it.

```text
Kiro / CLI / Python
        │
        ▼
   AgentRuntime ── Model (mock | openai)
        │        ├─ Tools (filesystem | shell)
        │        ├─ Skills (.agent/skills/*, bundled skills/*)
        │        └─ Workflow (requirement-analysis)
        ▼
     Output  ──►  Evaluation (deterministic)
```

## Architecture

| Layer | Module | Responsibility |
| --- | --- | --- |
| CLI | `agent_kit.cli.*` | parse arguments, call the runtime, print, set exit codes |
| Integration | `agent_kit.integrations.kiro`, `agent_kit.cli.kiro` | generate and inspect `.kiro/*` |
| Protocol | `agent_kit.mcp.*` | JSON-RPC 2.0 over stdio, tool registry |
| Runtime | `agent_kit.agent.runtime` | assemble model, tools, skills, workflow |
| Agent | `agent_kit.agent.agent` | model/tool loop and transcript |
| Model | `agent_kit.model.*` | `Model` contract, `MockModel`, `OpenAIModel`, registry |
| Tools | `agent_kit.tools.*` | `Tool` contract, restricted filesystem and shell |
| Skills | `agent_kit.skills.*` | `SKILL.md` discovery with project override |
| Workflow | `agent_kit.workflow.*` | named process + validation |
| Evaluation | `agent_kit.evaluation.*` | deterministic checks |
| Config | `agent_kit.config.*` | load/validate `.agent/config.yaml` |

Dependency direction is one-way: `cli → integrations/mcp → agent.runtime → {model,
tools, skills, workflow} → evaluation`. The runtime never imports the CLI.

## Components and Interfaces

### Model

```python
class Model(ABC):
    provider: str
    required_env_vars: tuple[str, ...]
    def generate(self, messages: list[Message], tools: list[ToolSpec] | None) -> ModelResponse: ...
```

`MockModel` returns a fixed summary or a scripted replay (used by tests).
`OpenAIModel` imports the SDK lazily, reads `OPENAI_API_KEY`, and maps
chat-completions messages/tool calls to provider-neutral objects.

### Tool

```python
class Tool(ABC):
    name: str; description: str; parameters: dict
    def spec(self) -> ToolSpec: ...
    def execute(self, **kwargs) -> ToolResult: ...
```

`FilesystemTool` resolves every path and rejects anything outside the project root.
`ShellTool` matches the executable against an exact whitelist and runs it with
`shell=False`, a bounded `cwd` and a timeout.

### Agent

`Agent.run(input, skill)` builds a system message from the base prompt, the skill
instructions and the tool inventory, then loops over model turns until a final
answer arrives. Tool failures become tool messages so the model can recover.
`AgentState` records the transcript and one `ToolInvocation` per executed call.

### Workflow

`RequirementAnalysisWorkflow` loads the skill, runs the agent and validates that
every required section is present. `AgentRuntime` builds the model, tools and skill
loader from configuration first, so the workflow stays declarative.

### MCP server

`MCPServer` implements `initialize`, `notifications/initialized`, `ping`,
`tools/list`, `tools/call`, `resources/list` and `prompts/list`. Tool handlers wrap
the runtime, so CLI and MCP invocations cannot diverge. stdout carries protocol
frames only; diagnostics use stderr.

## Data Models

- `.agent/config.yaml` — `agent`, `model`, `tools`, `skills`, `workflow`.
- `Message` / `ToolCall` / `ToolSpec` / `ModelResponse` — provider-neutral chat.
- `Skill` — name, instructions, source path.
- `WorkflowContext` / `WorkflowResult` — workflow input and validated output.
- `CheckResult` / `EvaluationResult` — deterministic check outcomes.
- `.kiro/specs/agent-kit-poc/.config.kiro` — `specId`, `workflowType`, `specType`.

## Error Handling

| Failure | Behaviour |
| --- | --- |
| Missing/invalid configuration | `ConfigError` with the command to fix it; CLI exits 1 |
| Unknown provider/tool/workflow/skill | error listing the available names |
| Model call failure | `ModelError`; run aborts with the provider message |
| Tool misuse | `ToolResult(success=False, …)` returned to the model |
| Tool boundary violation | `ToolError` converted into a failed tool result |
| Agent tool loop | stops after `max_iterations` with `AgentError` |
| MCP tool error | JSON-RPC error or `isError: true` content block |

## Security Considerations

1. Secrets are environment variables only; the Docker image bakes in none.
2. Filesystem access is confined to the resolved project root.
3. Shell execution is whitelist-only with no shell interpretation and a timeout.
4. MCP `autoApprove` covers read-only tools; `agent_kit_run_workflow` requires user
   approval because it can write files and call a model.
5. The Docker image runs as a non-root user.

## Testing Strategy

Unit tests cover configuration, skill loading, models, tools, the agent loop,
workflows, evaluation, scaffolding and the CLI. Integration tests run
`init → config → run → output → evaluate` with `MockModel`, compare generated
sections against the sample expectation, exercise a tool-using run, and confirm the
runtime works without the CLI. Kiro/MCP tests assert the generated file set, that
`install` is idempotent, and that MCP `initialize`/`tools/list`/`tools/call`
round-trip. No test requires an API key.
