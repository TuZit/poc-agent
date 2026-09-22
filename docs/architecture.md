# Architecture

> Companion to [`../specs/001-agent-kit-poc/plan.md`](../specs/001-agent-kit-poc/plan.md).
> This document explains the design; the plan explains the delivery.

## 1. Goals and non-goals

**Goals:** prove that an agent can be packaged as an installable CLI, that a
project can be initialised from a template, that model/tool/skill/workflow
selection can be externalised into configuration, that skills can ship separately
from the runtime, that sample input/output can drive regression testing, that one
orchestrator can select and coordinate several specialist agents, and that the
same runtime can serve an IDE (Kiro) as well as a shell.

**Non-goals (deliberate):** an LLM planner, parallel or queued agent execution,
inter-agent memory, memory/vector stores, RBAC, billing, Kubernetes, extra
providers beyond one real one plus a mock. See constitution 1.1.0 for the bound on
multi-agent.

## 2. Layering

```text
┌─────────────────────────────────────────────────────────────┐
│ Front ends                                                  │
│   cli/ (Typer: init doctor config run evaluate kiro mcp)    │
│   mcp/ (JSON-RPC 2.0 over stdio)                            │
│   integrations/kiro (generated workspace files)              │
└──────────────────────────┬──────────────────────────────────┘
                           │ uses
┌──────────────────────────▼──────────────────────────────────┐
│ agent/runtime.py   AgentRuntime(config)                     │
│   builds model, tools, skill loader, then runs a workflow   │
└──────────────────────────┬──────────────────────────────────┘
                           │ uses
┌──────────────────────────▼──────────────────────────────────┐
│ agent/agent.py   Agent (model ⇄ tool loop)                  │
│   model/  Model · MockModel · OpenAIModel                   │
│   tools/  Tool · FilesystemTool · ShellTool                 │
│   skills/ Skill · SkillLoader                               │
│   routing.py  TaskRouter (which agent should handle this?)  │
│   workflow/ Workflow · specialists · orchestration          │
└──────────────────────────┬──────────────────────────────────┘
                           │ uses
┌──────────────────────────▼──────────────────────────────────┐
│ evaluation/ (deterministic checks)  ·  config/  ·  paths/    │
└─────────────────────────────────────────────────────────────┘
```

Rules enforced by the layout (and by the constitution):

- `agent.runtime` and everything below it **must not import** `agent_kit.cli`.
- Only `model/*.py` may import a provider SDK, and only lazily.
- `evaluation` depends on nothing but the standard library, so it can validate
  output produced by any future producer.

## 3. Execution flow

```text
input text ──► WorkflowContext ──► Workflow.execute
                                      │
                                      ├─ runtime.load_skill(name)  →  SKILL.md
                                      ├─ runtime.build_agent()     →  Agent(model, tools)
                                      └─ Agent.run(input, skill)
                                             │
              ┌──────────────────────────────┘
              ▼
   system message = base prompt + skill instructions + tool inventory
              │
              ▼
        model.generate(messages, tool_specs)
              │
      ┌───────┴────────┐
      │ tool calls?    │
      └───┬────────┬───┘
         yes       no
          │         └─────► final Markdown ──► validate sections ──► WorkflowResult
          ▼
   execute each tool → append tool messages → loop (max_iterations)
```

Tool failures do not abort the run: they are appended as tool output so the model
can correct itself. Only model/provider errors, unknown workflows/skills and
exhausted iterations abort (each with a distinct exception type).

## 3.1 Orchestration flow

```text
request ──► OrchestrationWorkflow
                │
                ├─ read orchestrator.{strategy, agents, default_agents}
                ├─ TaskRouter.select(text)         ← keywords + structural signals
                │     └─ RoutingDecision(selected, signals, strategy, reason)
                ├─ for each selected agent: runtime.run_specialist(name, text)
                │     └─ its own skill → its own agent run → its own validation
                └─ build_report(...) → # Agent Orchestration Report
                      valid = report sections present AND every sub-result valid
```

Selection is deterministic and printed in the report, which is what makes
coordination testable offline. An LLM planner is a seam (`orchestrator.planner`),
not a requirement.

## 4. Contracts

### Configuration (`config/loader.py`)

```python
@dataclass(frozen=True)
class AppConfig:
    agent: AgentSection
    model: ModelSection          # provider, name, options
    tools: dict[str, ToolSection]  # enabled, options
    skills: list[str]
    workflow: WorkflowSection    # name, options
    project_root: Path
    config_path: Path
```

Unknown keys and an `options:` mapping are forwarded to the implementation, so a
provider can gain settings without a schema change. Invalid configuration raises
`ConfigError` with a runnable hint.

### Model

```python
class Model(ABC):
    provider: str
    required_env_vars: tuple[str, ...]
    def generate(self, messages, tools) -> ModelResponse
```

`ModelResponse(content, tool_calls)` is provider-neutral, which is why the agent
never sees SDK types. `MockModel` is the offline path; `OpenAIModel` maps to
chat-completions and back.

### Tool

```python
class Tool(ABC):
    name: str; description: str; parameters: dict
    def spec(self) -> ToolSpec
    def execute(self, **kwargs) -> ToolResult
```

`ToolResult(success, output)` is the only return channel; boundary violations
raise `ToolError`, which the agent converts to a failed result.

### Skill, Workflow

A `Skill` is `(name, instructions, path)` loaded from `SKILL.md`. A `Workflow` is
`execute(context, runtime) -> WorkflowResult`; `WorkflowResult` carries the output
plus a `valid` flag and the issues that made it invalid.

## 5. Security model

| Boundary | Enforcement |
| --- | --- |
| Secrets | environment variables only; `doctor` names the missing variable; never written to YAML, logs or the image |
| Filesystem | `FilesystemTool.resolve_inside_root()` resolves `..` and symlinks, then re-checks containment |
| Shell | exact whitelist (`python`, `pytest`, `git`), argument list, `shell=False`, fixed `cwd`, timeout |
| Provider SDK | optional extra; imported lazily, so it is absent from the default install and from tests |
| MCP | `autoApprove` limited to read-only tools; `agent_kit_run_workflow` needs approval because it writes files and calls a model |
| Container | non-root user, no secrets in any layer |

## 6. Bundled assets

Skills, templates, samples and Kiro integration files live at the repository root
(`skills/`, `templates/`, `samples/`, `integrations/`) and are force-included into
the wheel at `agent_kit/_bundled/` by hatchling. `paths.asset_dir(name)` prefers
the installed copy and falls back to the checkout, so `uv run` and `uv tool
install` behave identically. This is what lets an installed CLI scaffold a project
outside the source tree.

## 7. Extension seams

| Want to add… | Touch this | Runtime changes |
| --- | --- | --- |
| **Agent (specialist)** | `skills/<name>/SKILL.md` + `workflow/specialists.py` + `WORKFLOW_REGISTRY` + `orchestrator.agents` | none |
| Model provider | `model/<name>.py` + `MODEL_REGISTRY` | none |
| Tool | `tools/<name>.py` + `TOOL_REGISTRY` | none |
| Skill | a `SKILL.md` directory | none |
| Workflow | `workflow/workflow.py` + `WORKFLOW_REGISTRY` | none |
| Front end (IDE, service) | a new module calling `AgentRuntime`, or an MCP tool | none |

Future work (multiple models/agents, MCP federation, remote runtime, marketplace)
plugs into these seams without reshaping the core.

## 8. Where the POC stops

- One real provider, one mock provider.
- Three specialist agents, one orchestrator, one routing strategy set
  (`auto`/`all`), one evaluator strategy; the two new skills are skeletons.
- Orchestration is sequential and single-process: no queue, no parallelism, no
  inter-agent memory, no LLM planner.
- The MCP server implements the tool subset of the protocol (no resources,
  prompts, sampling, or notifications beyond `initialized`).
- `config set` rewrites the YAML file and therefore drops comments.
