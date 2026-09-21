# Implementation Plan: Agent Kit POC

**Feature branch:** `001-agent-kit-poc` · **Spec:** `specs/001-agent-kit-poc/spec.md`
**Stack:** Python 3.11+ · uv · Typer · PyYAML · pytest · Docker

## Summary

One installable Python package (`agent-kit-poc`) provides a Typer CLI and a
layered runtime. Configuration is a single YAML file; prompts are Markdown
skills; models and tools are pluggable behind small abstract interfaces. A
deterministic evaluator and a mock model keep the whole suite offline, and a Kiro
integration exposes the same runtime to an IDE through steering files, hooks and
a minimal stdio MCP server.

## Technical Context

| Concern | Decision | Reason |
| --- | --- | --- |
| Language | Python 3.11+ | union types, `tomllib`, modern typing; matches POC_TASK §3 |
| Packaging | `uv` + hatchling wheel | `uv sync`, `uv tool install .`, reproducible lock file |
| CLI | Typer | type-hint driven commands, minimal boilerplate |
| Config | `pyyaml` | human-editable, no code execution |
| Provider SDK | optional extra `[openai]` | keeps runtime and tests SDK-free |
| Tests | pytest, `MockModel` | hermetic suite, no API key |
| Assets | repo-root dirs force-included into the wheel | one canonical copy, works installed |
| Kiro | generated `.kiro/*` + stdio MCP server | native IDE integration without new deps |

## Project Structure

```text
dsh-build/
├── .specify/memory/constitution.md        # governing principles
├── specs/001-agent-kit-poc/               # spec.md, plan.md, tasks.md
├── src/agent_kit/
│   ├── cli/         main, init, config, doctor, run, evaluate, kiro, mcp, common
│   ├── agent/       agent (loop), runtime (assembly), state (transcript)
│   ├── model/       base (interfaces), mock, openai
│   ├── tools/       base (interfaces), filesystem, shell
│   ├── skills/      base (Skill), loader (SKILL.md discovery)
│   ├── workflow/    workflow (abstraction + requirement-analysis)
│   ├── evaluation/  evaluator (deterministic checks)
│   ├── integrations/kiro.py
│   ├── mcp/         server.py (JSON-RPC over stdio), tools.py
│   ├── config/      loader.py
│   ├── paths.py     bundled-asset resolution
│   └── scaffold.py  template rendering/copying
├── skills/requirement-analysis/{SKILL.md,templates/}
├── templates/project/{.agent/config.yaml,README.md}
├── integrations/kiro/                     # steering, hooks, specs, mcp.json templates
├── samples/requirement-analysis/{input,expected}/sample-001.md
├── tests/{unit,integration}/
├── docs/{architecture.md,development.md,kiro-integration.md}
├── Dockerfile · pyproject.toml · uv.lock · README.md · .env.example
```

## Component Contracts

### Configuration (`config/loader.py`)

`load_config(root) -> AppConfig`. Unknown provider keys and an `options:` mapping
are passed through as implementation options, so a provider can gain settings
without schema changes. Failures raise `ConfigError` with a runnable hint.

### Model (`model/`)

```python
class Model(ABC):
    provider: str
    required_env_vars: tuple[str, ...]
    def generate(self, messages, tools) -> ModelResponse: ...
```

`MockModel` returns a fixed summary (or a scripted replay), `OpenAIModel` lazily
imports the SDK, reads `OPENAI_API_KEY`, maps messages/tools to chat-completions
and parses tool calls back into provider-neutral objects. `MODEL_REGISTRY` maps
`model.provider` to a class.

### Tools (`tools/`)

```python
class Tool(ABC):
    name: str; description: str; parameters: dict
    def spec(self) -> ToolSpec
    def execute(self, **kwargs) -> ToolResult
```

Both built-in tools anchor to the project root at construction.
`FilesystemTool.resolve_inside_root()` re-validates the *resolved* path, so `..`
and symlink escapes fail. `ShellTool` matches the executable against a whitelist,
runs with `shell=False`, a bounded `cwd` and a timeout. Expected misuse returns
`ToolResult(success=False, ...)`; boundary violations raise `ToolError`.

### Skills (`skills/`)

`SkillLoader` searches `<project>/.agent/skills/` then the bundled `skills/`, so
projects override shipped skills. `SKILL.md` must exist and be non-empty.

### Agent (`agent/`)

`Agent.run(input, skill)` builds a system message (base prompt + skill
instructions + tool inventory), then loops: model → tool calls → execute →
append tool results → repeat, up to `max_iterations`. Tool failures are returned
to the model as text so it can recover. `AgentState` records the transcript and
every `ToolInvocation`.

### Workflow (`workflow/`)

`Workflow.execute(context, runtime) -> WorkflowResult`. `AgentRuntime` builds the
model, tools and skill loader from configuration, then delegates to the workflow.
`RequirementAnalysisWorkflow` loads the skill, runs the agent and validates the
output sections. New workflows register in `WORKFLOW_REGISTRY`.

### Evaluation (`evaluation/`)

`evaluate_text` / `evaluate_file` check existence, non-emptiness, required
sections (heading match, case-insensitive) and optional required concepts.
Results carry per-check detail and render as the `✓/✗ … Result: PASS` report.

### CLI (`cli/`)

Pure shell: parse → call runtime → print → exit code. `doctor` aggregates checks
with actionable hints; `run` writes the output and validates it; `evaluate`
exits non-zero on failure; `config` reads/updates YAML by dotted key.

### Kiro integration (`integrations/kiro.py`, `cli/kiro.py`, `mcp/`)

`install_kiro(project)` renders `integrations/kiro/` into the project
(`.kiro/steering`, `.kiro/hooks`, `.kiro/specs`, `.kiro/settings/mcp.json`).
`agent-kit mcp serve` speaks JSON-RPC 2.0 over stdio (`initialize`,
`tools/list`, `tools/call`) and reuses the runtime — no third-party MCP SDK.

## Security Model

1. Secrets only from the environment; never written into YAML or the image.
2. Filesystem tool confined to the resolved project root.
3. Shell tool: whitelist + argument list + `shell=False` + timeout + fixed cwd.
4. Tool failures degrade to model-visible text; they never crash the run.
5. Docker image runs as a non-root user with no secrets baked in.

## Testing Strategy

- **Unit:** configuration (valid/invalid/missing/options), skill loader
  (bundled, override, missing, empty), models (determinism, script replay, SDK
  mapping with a fake client, missing key), tools (round-trip, traversal,
  absolute paths, whitelist, metacharacter inertness), agent loop (tool round
  trip, unknown tool, boundary violation, max iterations, transcript), workflow
  (valid output, missing sections, skill resolution), evaluator, scaffold, CLI.
- **Integration:** `init → config → run → output → evaluate` with `MockModel`,
  no `OPENAI_API_KEY`; generated-vs-expected section comparison; a tool-using run
  through the pipeline; runtime used without the CLI.
- **Kiro/MCP:** generated file set, idempotence without `--force`, and MCP
  handshake plus `tools/list` / `tools/call`.

## Phases

1. **Setup** — package, uv, pytest, structure, README.
2. **CLI** — `init`, `doctor`, `run`, `evaluate`, `config`.
3. **Configuration** — loader + template.
4. **Model** — base, mock, openai, registry.
5. **Tools** — filesystem, shell, registry.
6. **Skills** — `SKILL.md`, loader.
7. **Workflow** — requirement-analysis + runtime.
8. **Evaluation** — deterministic evaluator.
9. **Integration test** — full flow.
10. **Docker** — image running the installed CLI.
11. **Kiro integration** — steering, hooks, spec artifacts, MCP server.

Each phase ends with a green `pytest` and an updated document.

## Risks & Mitigations

| Risk | Mitigation |
| --- | --- |
| Provider SDK leaks into the runtime | lazy import inside `OpenAIModel`; no SDK in tests |
| Assets missing after `uv tool install` | hatchling `force-include` + `paths.asset_dir()` dev fallback |
| Model-driven tools escaping the sandbox | resolve-then-validate paths; exact-match whitelist; `shell=False` |
| Non-deterministic tests | `MockModel` default output; no network in the suite |
| Kiro config drift | integration generated from versioned templates in `integrations/kiro/` |
