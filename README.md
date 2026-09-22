# Agent Kit POC

An installable **AI Agent Kit** proof of concept: install one CLI, scaffold a
project, point a YAML file at a model, and run an agent that loads a Markdown
skill, calls restricted tools, produces a structured output and validates that
output deterministically.

Inspired by the architecture and developer experience of
[GitHub Spec Kit](https://github.com/github/spec-kit) — spec-driven artifacts in
the repository, thin CLI, configuration over code — and designed to plug into
[AWS Kiro](https://kiro.dev) through steering files, hooks and an MCP server.

```text
Install → Init → Configure → Load skill → Run agent → Use tools → Generate output → Evaluate
```

> **Scope reminder.** This is a POC. Multi-agent orchestration, cloud deployment,
> RBAC, billing, vector stores and extra providers are deliberately **out of
> scope**; the architecture leaves seams for them (see
> [`docs/architecture.md`](docs/architecture.md)).

## Table of contents

- [What works today](#what-works-today)
- [Architecture](#architecture)
- [Requirements](#requirements)
- [Installation](#installation)
- [Initialization](#initialization)
- [Configuration](#configuration)
- [Running](#running)
- [Evaluation](#evaluation)
- [Testing](#testing)
- [Docker](#docker)
- [Kiro integration](#kiro-integration)
- [Extending the kit](#extending-the-kit)
  - [Add a model](#add-a-model)
  - [Add a tool](#add-a-tool)
  - [Add a skill](#add-a-skill)
  - [Add a workflow](#add-a-workflow)
- [Spec-driven development](#spec-driven-development)
- [Project layout](#project-layout)
- [Documentation map](#documentation-map)

## What works today

| Capability | Status |
| --- | --- |
| `agent-kit` CLI (`init`, `doctor`, `config`, `agents`, `run`, `evaluate`, `integration`, `kiro`, `mcp`) | ✅ |
| Standalone binary + one-line installer (no Python for end users) | ✅ |
| **Multi-agent orchestration** — a router selects specialist agents and aggregates their reports | ✅ |
| Specialist agents: requirement analysis, **code review**, **unit test generation** | ✅ |
| Project scaffolding from a bundled template | ✅ |
| `.agent/config.yaml` configuration, secrets from the environment | ✅ |
| `Model` abstraction: `OpenAIModel` + deterministic `MockModel` | ✅ |
| `Tool` abstraction: restricted `filesystem` + whitelisted `shell` | ✅ |
| Markdown skills (`SKILL.md`) with project-local overrides | ✅ |
| 4 workflows: `requirement-analysis`, `code-review`, `unit-test-generation`, `orchestration` | ✅ |
| Sample input + expected output | ✅ |
| Deterministic evaluator (no LLM judge) | ✅ |
| Unit + integration tests, offline (252 tests) | ✅ |
| Docker image | ✅ |
| Kiro integration (steering, hooks, prompts, custom agent, MCP server, specs) | ✅ |

## Architecture

```text
CLI (Typer)  ─┬─ init / doctor / config / agents
              ├─ run / evaluate
              ├─ kiro  (generate .kiro/*)
              └─ mcp   (stdio JSON-RPC server, 6 tools)
                    │
                    ▼
            Agent Runtime ──── Model ──── OpenAIModel | MockModel
                    │       ├── Tools ─── filesystem | shell
                    │       ├── Skills ── SKILL.md loader
                    │       └── Workflow
                    │             ├── orchestration ──► TaskRouter (which agent?)
                    │             ├── requirement-analysis
                    │             ├── code-review
                    │             └── unit-test-generation
                    ▼
                 Output (Markdown)  ── orchestrated report when several agents run
                    ▼
              Evaluation (deterministic checks, per-agent section sets)
```

The runtime is the product; the CLI is one front end. Dependencies run one way:
`cli / mcp / integrations → agent.runtime → {model, tools, skills, workflow} →
evaluation`. The runtime never imports the CLI, so it can be embedded anywhere.

## Requirements

- Python **3.11+**
- [`uv`](https://docs.astral.sh/uv/) (recommended) or pip
- Docker (optional, for the container image)
- `OPENAI_API_KEY` **only** if you use `model.provider: openai`

## Installation

**End users (no Python required)** — download the self-contained binary:

```bash
curl -fsSL https://YOUR-HOST/agent-kit/install.sh | sh   # macOS / Linux
irm https://YOUR-HOST/agent-kit/install.ps1 | iex        # Windows (PowerShell)
```

The binary bundles the runtime, skills, project template and the Kiro
integration. See [`docs/end-user-install.md`](docs/end-user-install.md) for the
manual install and troubleshooting.

**Developers** — install the package:

```bash
uv tool install .                    # from the project directory
uv tool install '.[openai]'          # ... with the OpenAI provider extra
uv sync --all-extras                 # or a dev checkout: .venv + pytest + ruff
uv run agent-kit --help
```

Verify the installation:

```bash
agent-kit --version
```

## Initialization

```bash
agent-kit init my-project                    # scaffold only
agent-kit init my-project --ai kiro          # scaffold + Kiro integration
agent-kit init my-project --force            # overwrite an existing directory
cd my-project
```

`init` creates:

```text
my-project/
├── .agent/
│   └── config.yaml            # agent, model, tools, skills, workflow
├── samples/
│   └── requirement-analysis/
│       ├── input/sample-001.md
│       └── expected/sample-001.md
└── README.md
```

It refuses to touch a non-empty directory unless `--force` is given.

## Configuration

Everything is configuration — no code changes to switch models, tools, skills or
workflows.

```yaml
# .agent/config.yaml
agent:
  name: my-project

model:
  provider: openai        # openai | mock
  name: gpt-4o-mini
  # options:
  #   temperature: 0.2

tools:
  filesystem:
    enabled: true         # read/write inside the project only
  shell:
    enabled: true         # whitelisted: python, pytest, git

skills:
  - requirement-analysis

workflow:
  name: requirement-analysis
```

Inspect and change it without an editor:

```bash
agent-kit config show
agent-kit config get model.provider
agent-kit config set model.provider mock
agent-kit config set tools.shell.enabled false
```

**Secrets are environment variables, never YAML.** Copy `.env.example` and export
it before running:

```bash
cp .env.example .env
set -a && source .env && set +a
```

## Running

```bash
agent-kit doctor                      # validate environment, model, tools, skills
agent-kit run                         # run the configured workflow
agent-kit run --input path/to/req.md --output output/req.md
agent-kit run --workflow requirement-analysis --skill requirement-analysis
```

`run` performs exactly this sequence:

1. load `.agent/config.yaml`
2. load the configured skill (`SKILL.md`)
3. initialise the model
4. initialise the enabled tools
5. build the agent context (system prompt + skill + tool inventory)
6. execute the configured workflow (model ⇄ tool loop)
7. validate required sections and write the output file

Offline mode — deterministic, no network, no API key:

```bash
agent-kit config set model.provider mock
agent-kit run
```

## Evaluation

```bash
agent-kit evaluate output/sample-001.md
agent-kit evaluate output/sample-001.md --require-concept "create product"
```

```text
Evaluation

✓ Output generated
✓ Objective
✓ Actors
✓ Functional Requirements
✓ Non-Functional Requirements
✓ Assumptions
✓ Open Questions

Result: PASS
```

The evaluator checks that the file exists, is non-empty, contains every required
section (case-insensitive heading match) and contains any requested concepts. It
exits non-zero on failure. Exact text matching and LLM-as-a-judge are
intentionally not used.

## Testing

```bash
uv run pytest                      # whole suite, offline
uv run pytest tests/unit -q        # unit tests only
uv run pytest tests/integration -v # end-to-end flow
```

The suite uses `MockModel` everywhere and never needs `OPENAI_API_KEY` or network
access. The integration test performs the full POC flow: `init → config → run →
output → evaluate → PASS`.

> 🧪 **Thực hiện UAT?** Xem [`docs/uat-tutorial.md`](docs/uat-tutorial.md) — hướng
> dẫn cài đặt & sử dụng kèm 35 test case nghiệm thu.

## Docker

```bash
docker build -t agent-kit-poc .

docker run --rm agent-kit-poc agent-kit --help
docker run --rm agent-kit-poc agent-kit doctor            # inside /work

# run against your project, with the key injected at run time
docker run --rm -v "$PWD:/work" -e OPENAI_API_KEY \
  agent-kit-poc agent-kit run --project /work
```

No secret is baked into the image, and the process runs as a non-root user.

## Kiro integration

Kiro is the agent tool integrated in this phase. It is installed through a
generic integration registry (`--integration` / `agent-kit integration ...`), so
other tools can be added later without touching the CLI — see
[`docs/agent-integrations.md`](docs/agent-integrations.md).

```bash
agent-kit init my-project --ai kiro          # at scaffold time (--ai is an alias)
agent-kit init my-project --integration kiro # same thing, canonical flag
agent-kit integration list                   # registered integrations + install state
agent-kit integration install kiro           # or later, inside the project
agent-kit integration status                 # check what is present
agent-kit integration uninstall kiro --yes   # remove only the managed files

agent-kit kiro install | status | uninstall  # shorthand alias
```

This writes:

```text
.kiro/
├── steering/
│   ├── agent-kit.md                   # inclusion: always  — workspace + tool guide
│   └── agent-kit-requirements.md      # inclusion: fileMatch — summary contract
├── hooks/
│   ├── agent-kit-context.json         # UserPromptSubmit → inject project capabilities
│   ├── agent-kit-evaluate.json        # PostFileSave → validate output/*.md
│   └── agent-kit-run.json             # Manual → run the workflow
├── agents/agent-kit.json              # custom Kiro agent wired to the MCP tools
├── prompts/
│   ├── agent-kit.run.md
│   └── agent-kit.evaluate.md
├── settings/mcp.json                  # registers `agent-kit mcp serve`
└── specs/agent-kit-poc/
    ├── requirements.md                # EARS format
    ├── design.md
    ├── tasks.md
    └── .config.kiro
```

Kiro then gets agent-kit as four MCP tools — `agent_kit_run_workflow`,
`agent_kit_evaluate`, `agent_kit_capabilities`, `agent_kit_read_skill` — plus the
above context and automation. Existing `.kiro` files are never overwritten unless
you pass `--force`. Details, formats and troubleshooting:
[`docs/kiro-integration.md`](docs/kiro-integration.md).

The MCP server can also be driven directly:

```bash
agent-kit mcp tools
agent-kit mcp call agent_kit_capabilities
agent-kit mcp call agent_kit_run_workflow --arguments '{"input_text": "Build a todo API"}'
```

## Agents & orchestration

Three specialist agents ship with the kit, plus one orchestrator that routes a
request to them:

| Agent | Use it when | Output contract |
| --- | --- | --- |
| `requirement-analysis` | a requirement or user story needs a structured summary | Objective, Actors, Functional Requirements, NFRs, Assumptions, Open Questions |
| `code-review` | a diff, patch or file must be reviewed | Summary, Findings, Recommendations, Open Questions |
| `unit-test-generation` | tests must be planned for a unit of code | Summary, Test Scope, Test Cases, Edge Cases, Open Questions |
| `orchestration` | the request is broad or mixes concerns | Request Analysis, Summary + one section per selected agent |

```bash
agent-kit agents                                            # list agents + orchestrator setup
agent-kit run --workflow code-review                        # one agent
agent-kit run --workflow orchestration                      # router picks the agents
agent-kit run --workflow orchestration --agents code-review # force an agent
agent-kit evaluate output/sample-code-review.md --workflow code-review
```

Routing is deterministic (keywords + diff/test structural signals) and the
aggregated report states *why* each agent ran. In Kiro the same thing is available
as slash commands (`agent-kit.orchestrate`, `agent-kit.code-review`, ...), custom
agents (`kiro-cli --agent code-review`) and MCP tools. Full guide:
[`docs/multi-agent.md`](docs/multi-agent.md).

> The two new skills are **skeletons** on purpose: each `SKILL.md` ends with a
> `## TODO (team to complete)` checklist for the team's real review/testing standard.

## Extending the kit

### Add a model

1. Subclass `Model` in `src/agent_kit/model/<provider>.py` (lazy-import the SDK):

```python
class AnthropicModel(Model):
    provider = "anthropic"
    required_env_vars = ("ANTHROPIC_API_KEY",)

    def generate(self, messages, tools=None) -> ModelResponse:
        ...
```

2. Register it in `src/agent_kit/model/__init__.py`:

```python
MODEL_REGISTRY = {"mock": MockModel, "openai": OpenAIModel, "anthropic": AnthropicModel}
```

3. `agent-kit config set model.provider anthropic`. The agent is untouched, and
   `doctor` automatically reports the new provider's required environment variable.

### Add a tool

1. Subclass `Tool` in `src/agent_kit/tools/<name>.py`:

```python
class HttpTool(Tool):
    name = "http"
    description = "Fetch a URL."
    parameters = {
        "type": "object",
        "properties": {"url": {"type": "string"}},
        "required": ["url"],
    }

    def execute(self, url: str = "", **_: object) -> ToolResult:
        return ToolResult(success=True, output=f"would fetch {url}")
```

2. Register it in `src/agent_kit/tools/__init__.py` (`TOOL_REGISTRY`).
3. Enable it in configuration:

```yaml
tools:
  http:
    enabled: true
```

Keep the security boundary explicit: validate inputs, confine side effects, and
return `ToolResult(success=False, ...)` for expected misuse.

### Add a skill

Skills are Markdown — no Python needed:

```bash
mkdir -p .agent/skills/api-review/templates
$EDITOR .agent/skills/api-review/SKILL.md
```

```markdown
# API Review

## Purpose

Review an API specification.

## Instructions

1. Identify the endpoints.
2. Check request/response schemas.
3. List security gaps.

## Output Format

Return `# API Review` with sections: Endpoints, Schemas, Security, Open Questions.
```

Select it in `.agent/config.yaml` (`skills: [api-review]`). Project-local skills
shadow shipped skills of the same name, so a project can override
`requirement-analysis` without touching the package.

### Add a workflow

1. Subclass `Workflow` in `src/agent_kit/workflow/workflow.py` (or a new module):

```python
class CodeReviewWorkflow(Workflow):
    name = "code-review"
    default_skill = "code-review"

    def execute(self, context, runtime):
        skill = context.skill or runtime.load_skill(self.default_skill)
        result = runtime.build_agent().run(context.input_text, skill=skill)
        issues = [f"Missing section: {s}" for s in find_missing_sections(result.output, SECTIONS)]
        return WorkflowResult(
            workflow=self.name, output=result.output, valid=not issues, issues=issues
        )
```

2. Register it in `WORKFLOW_REGISTRY`.
3. `agent-kit config set workflow.name code-review`.

## Spec-driven development

This repository follows the Spec Kit flow: a constitution, a specification, a
plan and a task list, all versioned next to the code.

```text
.specify/memory/constitution.md     governing principles
specs/001-agent-kit-poc/spec.md     what and why (user stories, acceptance criteria)
specs/001-agent-kit-poc/plan.md     how (stack, components, testing, phases)
specs/001-agent-kit-poc/tasks.md    ordered, checkable work items
```

Kiro users get the same content in Kiro's own format under
`.kiro/specs/agent-kit-poc/` (`requirements.md` in EARS notation, `design.md`,
`tasks.md`).

## Project layout

```text
dsh-build/
├── .specify/memory/constitution.md
├── specs/001-agent-kit-poc/{spec,plan,tasks}.md
├── src/agent_kit/
│   ├── cli/            main, init, config, doctor, run, evaluate, kiro, mcp, common
│   ├── agent/          agent (loop), runtime (assembly), state (transcript)
│   ├── model/          base, mock, openai
│   ├── tools/          base, filesystem, shell
│   ├── skills/         base, loader
│   ├── workflow/       workflow (abstraction + requirement-analysis)
│   ├── evaluation/     evaluator
│   ├── integrations/   kiro
│   ├── mcp/            server, tools
│   ├── config/         loader
│   ├── paths.py        bundled-asset resolution
│   └── scaffold.py     template rendering/copying
├── skills/requirement-analysis/{SKILL.md,templates/}
├── templates/project/                # what `init` copies
├── integrations/kiro/                # what `kiro install` copies
├── samples/requirement-analysis/{input,expected}/sample-001.md
├── tests/{unit,integration}/
├── docs/{architecture,development,kiro-integration}.md
├── Dockerfile · pyproject.toml · uv.lock · .env.example
└── README.md
```

## Documentation map

| Document | Contents |
| --- | --- |
| [`docs/multi-agent.md`](docs/multi-agent.md) | **Agents & orchestrator (tiếng Việt)** — 3 agent, routing, CLI/MCP/Kiro, cách thêm agent |
| [`docs/end-user-install.md`](docs/end-user-install.md) | **Cài đặt cho người dùng cuối (tiếng Việt)** — binary không cần Python, Docker, xử lý sự cố |
| [`docs/uat-tutorial.md`](docs/uat-tutorial.md) | **UAT guide (tiếng Việt)** — cài đặt, sử dụng, 35 test case nghiệm thu, xử lý sự cố |
| [`docs/agent-integrations.md`](docs/agent-integrations.md) | **Tích hợp agent tool (tiếng Việt)** — kiến trúc registry, cách thêm tool mới, tham chiếu format |
| [`docs/packaging-deployment.md`](docs/packaging-deployment.md) | **Packaging & deployment (tiếng Việt)** — build wheel, nhúng asset, Docker, CI/CD, secret, rollback |
| [`docs/architecture.md`](docs/architecture.md) | layers, contracts, data flow, security model, extension seams |
| [`docs/development.md`](docs/development.md) | local setup, tests, debugging, adding components, demo checklist |
| [`docs/kiro-integration.md`](docs/kiro-integration.md) | Kiro file formats, MCP tools, hooks, steering, troubleshooting |
| [`.specify/memory/constitution.md`](.specify/memory/constitution.md) | the principles this code follows |
| [`specs/001-agent-kit-poc/spec.md`](specs/001-agent-kit-poc/spec.md) | functional requirements and acceptance criteria |

## License

MIT (POC).
