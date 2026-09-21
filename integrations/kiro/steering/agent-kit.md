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
| `.agent/config.yaml` | single source of truth: agent, model, tools, skills, workflow |
| `.agent/skills/<name>/SKILL.md` | project-local skill overrides (Markdown instructions) |
| `samples/requirement-analysis/input/` | example requirement input |
| `output/` | generated requirement summaries |
| `.kiro/steering/` | the context you are reading |
| `.kiro/hooks/` | automated `agent-kit` commands |
| `.kiro/specs/agent-kit-poc/` | requirements, design and tasks for this workspace |

## Which tool to reach for

1. **MCP tools (preferred)**
   - `agent_kit_run_workflow` — turn requirement text or a requirement file into a
     structured requirement summary.
   - `agent_kit_evaluate` — deterministic PASS/FAIL check of a summary.
   - `agent_kit_capabilities` — the resolved configuration and available capabilities.
   - `agent_kit_read_skill` — the full Markdown instructions of a skill.
2. **CLI** — `agent-kit doctor`, `agent-kit run`, `agent-kit evaluate <file>`,
   `agent-kit config show|get|set`.
3. **Python** — `AgentRuntime(load_config(".")).run_workflow(text)`.

Read a skill with `agent_kit_read_skill` before re-implementing its instructions by hand.

## Working rules

- Prefer the MCP tools over hand-writing a requirement summary.
- Never invent requirement content. Anything not stated by the input belongs under
  **Open Questions**, not in the requirements.
- Run `agent-kit evaluate <file>` (or `agent_kit_evaluate`) before reporting a
  summary as finished.
- Changing behaviour means changing configuration — `model.provider`, `model.name`,
  `tools.*.enabled`, `skills`, `workflow.name` — never editing Python.
- Secrets live in environment variables only (`OPENAI_API_KEY`). Never write a key
  into `.agent/config.yaml`.
- For offline work use the deterministic provider:
  `agent-kit config set model.provider mock`.
