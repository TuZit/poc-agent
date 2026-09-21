# Feature Specification: Agent Kit POC

**Feature branch:** `001-agent-kit-poc`
**Status:** Implemented
**Input:** `POC_TASK.md` — build a small POC for an installable AI Agent Kit
inspired by the architecture and developer experience of GitHub Spec Kit.

## Overview

A developer installs one CLI (`agent-kit`), scaffolds a project from a bundled
template, points a YAML file at a model and a workflow, and runs an agent that
loads a Markdown skill, calls restricted tools, produces a structured output and
validates that output deterministically.

```text
Install → Init → Configure → Load skill → Run agent → Use tools → Generate output → Evaluate
```

## User Scenarios & Testing

### User Story 1 — Install the kit and scaffold a project (P1)

A developer wants a runnable project skeleton without reading the source.

**Why P1:** nothing else can be exercised until a project exists.

**Independent test:** `agent-kit init demo-project` creates
`.agent/config.yaml`, `README.md` and `samples/`; a second run refuses to
overwrite without `--force`.

**Acceptance scenarios:**

1. **Given** an empty directory, **when** `agent-kit init my-project` runs,
   **then** the project contains `.agent/config.yaml` with agent, model, tools,
   skills and workflow sections, plus `README.md` and the sample input/output.
2. **Given** an existing non-empty directory, **when** `init` runs without
   `--force`, **then** it exits non-zero, explains why, and changes nothing.
3. **Given** the same directory, **when** `init --force` runs, **then** template
   files are restored and unrelated files are preserved.

### User Story 2 — Diagnose the environment before running (P1)

A developer wants to know *why* the agent cannot run, with an actionable fix.

**Independent test:** `agent-kit doctor` prints ✓/✗ per check and exits 0 only
when every check passes.

**Acceptance scenarios:**

1. **Given** a mock-configured project, **when** `doctor` runs, **then** Python
   version, configuration, model, tools, skills and workflow are reported ✓ and
   "Agent environment is ready." is printed.
2. **Given** no `.agent/config.yaml`, **when** `doctor` runs, **then** the
   configuration check fails with the hint to run `agent-kit init`.
3. **Given** `model.provider: openai` and no `OPENAI_API_KEY`, **when** `doctor`
   runs, **then** the environment is reported NOT ready with the variable named
   and the offline alternative offered.

### User Story 3 — Run the agent end to end (P1)

A developer wants a requirement analysed into a structured summary.

**Independent test:** `agent-kit run` writes `output/sample-001.md` whose
sections satisfy the evaluator.

**Acceptance scenarios:**

1. **Given** a configured project, **when** `run` executes, **then** it loads the
   configuration, loads the configured skill, initialises the model and enabled
   tools, executes the workflow and writes the output file.
2. **Given** an unknown workflow or skill, **when** `run` executes, **then** it
   exits non-zero with the list of available options.
3. **Given** the mock provider, **when** `run` executes, **then** no network call
   and no API key are required.
4. **Given** a real provider, **when** the model requests a tool, **then** the
   tool result is fed back to the model before the final answer.

### User Story 4 — Evaluate output without an LLM judge (P2)

A developer wants a deterministic regression gate.

**Independent test:** `agent-kit evaluate output/sample-001.md` exits 0 on good
output and 1 on bad output.

**Acceptance scenarios:**

1. **Given** output containing all required sections, **when** it is evaluated,
   **then** every check is ✓ and the result is PASS.
2. **Given** output missing a section, **when** it is evaluated, **then** that
   section is marked ✗ and the result is FAIL.
3. **Given** a missing or empty file, **when** it is evaluated, **then** the
   "Output generated" check fails and the exit code is 1.
4. **Given** `--require-concept <keyword>`, **when** the keyword is absent,
   **then** the concept check fails.

### User Story 5 — Extend the kit (P2)

A developer wants to add a model, tool, skill or workflow without rewriting the
runtime.

**Independent test:** a new skill is added as a Markdown directory and selected
through configuration; a new tool is registered and enabled through
configuration.

**Acceptance scenarios:**

1. **Given** a new `.agent/skills/<name>/SKILL.md`, **when** the skill is
   configured, **then** the agent receives those instructions verbatim.
2. **Given** a project-local skill with the same name as a shipped skill,
   **when** it is loaded, **then** the project-local copy wins.
3. **Given** a tool disabled in configuration, **when** the runtime is built,
   **then** the tool is absent from the agent's tool list.

### User Story 6 — Use the kit from Kiro (P2)

A developer working in Kiro wants agent-kit available as a first-class tool,
with project context and automation.

**Independent test:** `agent-kit init <project> --ai kiro` (or
`agent-kit kiro install`) creates Kiro steering, hooks, spec artifacts and an MCP
server registration; `agent-kit mcp serve` answers MCP `initialize`,
`tools/list` and `tools/call`.

**Acceptance scenarios:**

1. **Given** a project, **when** the Kiro integration is installed, **then**
   `.kiro/steering/`, `.kiro/hooks/`, `.kiro/specs/` and
   `.kiro/settings/mcp.json` exist and reference `agent-kit`.
2. **Given** the MCP server is running, **when** a client lists tools, **then**
   agent-kit capabilities (run workflow, evaluate output, list skills) are
   returned; **when** it calls one, **then** the result is the same as the
   equivalent CLI invocation.
3. **Given** an already-installed integration, **when** it is installed again
   without `--force`, **then** existing files are not overwritten.

### Edge cases

- Configuration YAML is malformed, empty, or missing a required key.
- `OPENAI_API_KEY` is present but the `openai` extra is not installed.
- The agent calls an unknown tool, or a tool with invalid arguments.
- A tool call attempts to escape the project root.
- The model loops on tool calls and never produces a final answer.
- The configured skill file is missing or empty.

## Requirements

### Functional

- **FR-001:** The CLI MUST be named `agent-kit` and expose `init`, `doctor`,
  `config`, `run`, `evaluate` (plus `kiro` and `mcp` integration commands).
- **FR-002:** `init` MUST scaffold from a bundled template and MUST NOT
  overwrite a non-empty directory without `--force`.
- **FR-003:** Configuration MUST come from `.agent/config.yaml` and MUST cover
  agent name, model provider/name, per-tool enablement, skills and workflow.
- **FR-004:** Secrets MUST be read from environment variables only.
- **FR-005:** The runtime MUST implement `Model`, `Tool`, `Skill` and `Workflow`
  abstractions; the agent MUST depend on `Model`, not on a provider SDK.
- **FR-006:** One provider (`openai`) and one offline provider (`mock`) MUST be
  implemented.
- **FR-007:** The filesystem tool MUST restrict access to the project directory.
- **FR-008:** The shell tool MUST allow only `python`, `pytest` and `git`, with
  no shell interpretation.
- **FR-009:** Skills MUST be Markdown `SKILL.md` directories; instructions MUST
  NOT be hard-coded in Python.
- **FR-010:** The `requirement-analysis` workflow MUST load the skill, run the
  agent, validate required sections and return the result.
- **FR-011:** The evaluator MUST deterministically check existence, non-emptiness,
  required sections and optional required concepts.
- **FR-012:** The package MUST ship a project template, one skill, sample
  input/expected output and the Kiro integration templates.
- **FR-013:** The test suite MUST include unit tests for configuration, skills,
  models, tools, workflow, evaluator and CLI, plus one end-to-end integration
  test that uses `MockModel` and no API key.
- **FR-014:** A Dockerfile MUST build an image that runs the installed CLI
  without embedding secrets.
- **FR-015:** The Kiro integration MUST generate steering, hooks, spec artifacts
  and an MCP server registration, and MUST expose the runtime through a minimal
  stdio MCP server.

### Key entities

- **Configuration (`AppConfig`)** — agent, model, tools, skills, workflow,
  project root, config path.
- **Model** — provider, name, `generate(messages, tools) -> ModelResponse`.
- **Message / ToolCall / ToolSpec / ModelResponse** — provider-neutral
  conversation primitives.
- **Tool** — name, description, JSON-schema parameters, `execute(**kwargs)`.
- **Skill** — name, Markdown instructions, source path.
- **AgentState / ToolInvocation** — transcript and tool audit trail for one run.
- **WorkflowContext / WorkflowResult** — workflow input and validated output.
- **CheckResult / EvaluationResult** — deterministic check outcomes.

## Success Criteria

- **SC-001:** `uv sync && pytest` passes from a clean checkout, offline.
- **SC-002:** `uv tool install .` exposes a working `agent-kit` binary whose
  bundled assets resolve outside the source tree.
- **SC-003:** The demo (`init → config → run → evaluate`) completes with
  `Evaluation Result: PASS` using the mock provider.
- **SC-004:** Adding a skill requires no Python change; adding a tool requires
  one subclass and one registry line; adding a model requires one subclass and
  one registry line.
- **SC-005:** No test imports a provider SDK, and no test requires a secret.

## Out of Scope

Multi-agent orchestration, production authentication, Kubernetes, cloud
deployment, complex memory, vector databases, enterprise RBAC, UI, billing,
advanced observability, additional LLM providers, complex MCP ecosystems. The
architecture must allow them; this POC must not implement them.
