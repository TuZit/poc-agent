---
inclusion: always
---

# Agent Kit POC (agent-kit)

This workspace is scaffolded by **Agent Kit POC** — an installable,
configuration-driven AI agent kit. The same runtime reaches you in three ways: as
an MCP server, as the `agent-kit` CLI, and as a Python library.

## Workspace map

| Path | Purpose |
| --- | --- |
| `.agent/config.yaml` | single source of truth: agent, model, tools, skills, workflow, orchestrator |
| `.agent/skills/<name>/SKILL.md` | project-local skill overrides (Markdown instructions) |
| `samples/<agent>/input/` | example input per agent |
| `output/` | generated reports |
| `.kiro/steering/` | the context you are reading |
| `.kiro/hooks/` | automated `agent-kit` commands |
| `.kiro/specs/agent-kit-poc/` | requirements, design and tasks for this workspace |

## Specialist agents

| Agent (`workflow=`) | Use it when | Output contract |
| --- | --- | --- |
| `requirement-analysis` | a requirement, user story or feature needs a structured summary | Objective, Actors, Functional Requirements, Non-Functional Requirements, Assumptions, Open Questions |
| `code-review` | a diff, patch or file must be reviewed | Summary, Findings, Recommendations, Open Questions |
| `unit-test-generation` | tests must be planned or written for a unit of code | Summary, Test Scope, Test Cases, Edge Cases, Open Questions |
| `orchestration` | the request is broad or mixes concerns; let the router choose | Request Analysis, Summary + one section per selected agent |

The orchestrator is the "big agent": it analyses the request, picks the
specialist agents that fit and runs them, then aggregates one report. In Kiro you
can either let it decide (`agent_kit_orchestrate`) or drive the choice yourself.

## Which tool to reach for

1. **MCP tools (preferred)**
   - `agent_kit_list_agents` — the specialist agents, when to use each, their contracts.
   - `agent_kit_orchestrate` — analyse a request, select agents and run them (aggregated report).
   - `agent_kit_run_workflow` — run one agent (`workflow=requirement-analysis|code-review|unit-test-generation`).
   - `agent_kit_evaluate` — deterministic PASS/FAIL check of a generated report.
   - `agent_kit_capabilities` — the resolved configuration and available capabilities.
   - `agent_kit_read_skill` — the full Markdown instructions of a skill.
2. **CLI** — `agent-kit agents`, `agent-kit doctor`, `agent-kit run --workflow <name>`,
   `agent-kit run --workflow orchestration --agents code-review`, `agent-kit evaluate <file> --workflow <name>`.
3. **Python** — `AgentRuntime(load_config(".")).run_workflow(text, workflow_name="code-review")`.

Read a skill with `agent_kit_read_skill` before re-implementing its instructions by hand.

## Working rules

- Pick the narrowest agent that fits; use the orchestrator when the request is mixed.
- Never invent content the input does not state: unsupported details belong under
  **Open Questions**, not in the report body.
- Validate before reporting success: `agent-kit evaluate <file> --workflow <agent>`
  (or `agent_kit_evaluate`) must return `Result: PASS`.
- Changing behaviour means changing configuration — `model.provider`, `model.name`,
  `tools.*.enabled`, `skills`, `workflow.name`, `orchestrator.*` — never editing Python.
- Secrets live in environment variables only (`OPENAI_API_KEY`). Never write a key
  into `.agent/config.yaml`.
- For offline work use the deterministic provider:
  `agent-kit config set model.provider mock`.
