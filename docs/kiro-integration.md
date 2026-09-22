# Kiro integration

Agent-kit plugs into [Kiro](https://kiro.dev) as a **local MCP server** plus
workspace **steering**, **hooks**, **prompts**, a **custom agent** and a
**spec** in Kiro's own format. The same runtime that powers `agent-kit run`
answers Kiro's tool calls, so an IDE session and a terminal session cannot drift.

```bash
agent-kit init my-project --ai kiro   # scaffold + integration
agent-kit kiro install                # inside an existing project
agent-kit kiro install --force        # overwrite managed files
agent-kit kiro status                 # what is present / missing (exit 1 if missing)
agent-kit kiro uninstall              # remove only the managed files
```

## 1. What gets installed

```text
.kiro/
├── steering/                            # 4 files: 1 always + 3 fileMatch contracts
│   ├── agent-kit.md                     # inclusion: always (agents + tools + rules)
│   ├── agent-kit-requirements.md        # fileMatch: requirement summary contract
│   ├── agent-kit-code-review.md         # fileMatch: code review contract
│   └── agent-kit-unit-test.md           # fileMatch: unit test plan contract
├── hooks/                               # 4 v1 hooks
│   ├── agent-kit-context.json           # UserPromptSubmit → inject capabilities
│   ├── agent-kit-evaluate.json          # PostFileSave → validate the output
│   ├── agent-kit-run.json               # Manual → run the configured workflow
│   └── agent-kit-orchestrate.json       # Manual → run the orchestrator
├── agents/                              # 3 custom agents
│   ├── agent-kit.json                   # orchestrator (all agent-kit tools)
│   ├── code-review.json                 # code review agent
│   └── unit-test.json                   # unit test agent
├── prompts/                             # 5 file-based slash commands
│   ├── agent-kit.orchestrate.md
│   ├── agent-kit.code-review.md
│   ├── agent-kit.unit-test.md
│   ├── agent-kit.run.md
│   └── agent-kit.evaluate.md
├── settings/
│   └── mcp.json                         # registers `agent-kit mcp serve`
└── specs/
    └── agent-kit-poc/
        ├── requirements.md              # EARS notation
        ├── design.md
        ├── tasks.md
        └── .config.kiro                 # specId / workflowType / specType
```

`install` never overwrites an existing file unless `--force` is passed, so you can
edit the steering and hooks without losing them on the next install. The spec id
in `.config.kiro` is generated once.

## 2. MCP server

`.kiro/settings/mcp.json`:

```json
{
  "mcpServers": {
    "agent-kit": {
      "command": "agent-kit",
      "args": ["mcp", "serve"],
      "env": {},
      "disabled": false,
      "autoApprove": [
        "agent_kit_capabilities",
        "agent_kit_evaluate",
        "agent_kit_read_skill"
      ]
    }
  }
}
```

Kiro runs the server with the workspace as the working directory, so the tools
operate on *this* project. `agent-kit mcp serve` speaks JSON-RPC 2.0 over stdio
(`initialize`, `notifications/initialized`, `ping`, `tools/list`, `tools/call`,
`resources/list`, `prompts/list`); stdout carries protocol frames only, and
diagnostics go to stderr.

### The four tools

| Tool | Arguments | What it does |
| --- | --- | --- |
| `agent_kit_list_agents` | — | the specialist agents, when to use each, their output contracts |
| `agent_kit_orchestrate` | `input_text`/`input_file`, optional `agents`, `strategy`, `write_output` | analyses the request, selects agents, runs them, returns one aggregated report |
| `agent_kit_run_workflow` | `input_text` or `input_file`, optional `workflow`, `skill`, `agents`, `strategy`, `write_output` | runs one agent (`requirement-analysis`, `code-review`, `unit-test-generation`) |
| `agent_kit_evaluate` | `output_file` or `text`, optional `required_concepts` | deterministic section/concept check, returns the PASS/FAIL report |
| `agent_kit_capabilities` | — | resolved configuration: model, tools, skills, workflow, orchestrator |
| `agent_kit_read_skill` | `name` | the full Markdown instructions of a skill |

All paths are resolved against the project root and refused if they escape it.

**Why `agent_kit_run_workflow` and `agent_kit_orchestrate` are not auto-approved:**
they can call a model (cost) and write files. The four read-only tools
(`list_agents`, `capabilities`, `evaluate`, `read_skill`) are auto-approved to keep
the session fluid; add the mutating ones to `autoApprove` if you accept that.

Try it without an IDE:

```bash
agent-kit mcp tools
agent-kit mcp call agent_kit_capabilities
agent-kit mcp call agent_kit_run_workflow --arguments '{"input_text": "Build a todo API", "write_output": "output/todo.md"}'
agent-kit mcp call agent_kit_evaluate --arguments '{"output_file": "output/todo.md"}'
```

Or speak the protocol directly:

```bash
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18"}}' \
  '{"jsonrpc":"2.0","method":"notifications/initialized"}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
  | agent-kit mcp serve
```

## 3. Steering

Steering files are Markdown with optional YAML frontmatter; the `inclusion` key
accepts `always`, `fileMatch`, `manual` or `auto`.

`agent-kit.md` (`inclusion: always`) describes the workspace map, which tool to
reach for, and the working rules (prefer MCP tools, never invent requirements, run
the evaluator before claiming success, secrets stay in the environment).

`agent-kit-requirements.md` (`inclusion: fileMatch`) is attached only when you
touch sample, output or spec Markdown, and states the required section contract:

```markdown
---
inclusion: fileMatch
fileMatchPattern: ["samples/**/*.md", "output/**/*.md", "specs/**/*.md", ".kiro/specs/**/*.md"]
---

# Requirement summary contract
...
```

Edit these freely — they are your project's context, and `kiro install` will not
clobber them.

## 4. Hooks

Kiro's current hook format is `v1` (`kiro.dev/docs/hooks.md`): one JSON file per
concern in `.kiro/hooks/`, containing a `hooks` array with `trigger`, optional
`matcher` (regex) and an `action` of type `command` or `agent`.

| File | Trigger | Action | Why |
| --- | --- | --- | --- |
| `agent-kit-context.json` | `UserPromptSubmit` | `agent-kit mcp call agent_kit_capabilities` | STDOUT of an exit-0 hook is added to context, so Kiro always knows the active model, tools, agents and workflow |
| `agent-kit-evaluate.json` | `PostFileSave` (matcher `output/.*\.md$`) | `agent-kit evaluate output/sample-001.md --workflow requirement-analysis` | a saved summary is validated immediately |
| `agent-kit-run.json` | `Manual` | `agent-kit run --input … --output …` | one-click run from the hooks panel |
| `agent-kit-orchestrate.json` | `Manual` | `agent-kit run --workflow orchestration --output output/sample-orchestration.md` | one-click orchestration (router picks the agents) |

Exit codes: `0` success (STDOUT may join the context), `2` blocks the action, any
other value is a warning and the session continues.

> **Format history.** Older Kiro IDE releases used `.kiro.hook` files with
> `when`/`then` blocks; IDE 1.0 replaced that format. agent-kit generates the
> current `v1` JSON hooks only, and `kiro_status` will flag the managed set as
> complete without expecting any `.kiro.hook` file.

## 5. Custom agent

Three Kiro agents are generated: `agent-kit` (orchestrator), `code-review` and
`unit-test`. They all reach the same MCP server; only the read-only tools are
auto-approved, and each specialist agent ships its own resources and prompt.

`.kiro/agents/agent-kit.json` (the orchestrator):

```json
{
  "name": "agent-kit",
  "prompt": "file://.kiro/steering/agent-kit.md",
  "tools": ["read", "write", "@agent-kit"],
  "allowedTools": ["read", "@agent-kit/agent_kit_capabilities", "@agent-kit/agent_kit_evaluate", "@agent-kit/agent_kit_read_skill"],
  "resources": ["file://README.md", "file://.kiro/steering/**/*.md", "skill://.agent/skills/**/SKILL.md"],
  "includeMcpJson": true
}
```

Start it with `kiro-cli --agent agent-kit` (binary is `kiro-cli`), or swap agents
in-session. Write access is granted but the mutating MCP tool still requires
approval.

## 6. Prompts

`.kiro/prompts/agent-kit.run.md` and `agent-kit.evaluate.md` are file-based
prompts in the same style as Spec Kit's `--integration kiro-cli` output
(`.kiro/prompts/speckit.<command>.md`). Each states the steps, the rules and a CLI
fallback in case the MCP server is not running.

## 7. Spec in Kiro's format

`.kiro/specs/agent-kit-poc/` mirrors the repository spec using Kiro's conventions:

- `requirements.md` — `# Requirements Document — <title>`, Introduction, Glossary,
  Requirements with `**User Story:**` and `#### Acceptance Criteria` written in
  EARS (`WHEN <event>, THE SYSTEM SHALL <response>`).
- `design.md` — architecture, components, data models, error handling, security,
  testing.
- `tasks.md` — `# Implementation Plan: <title>`, `## Tasks`, checkboxes
  (`- [x] 1.`, `- [x] 1.1`) with `- _Requirements: 1.1, 1.2_` traceability.
- `.config.kiro` — `specId`, `workflowType: requirements-first`, `specType: feature`.

The repo-side equivalents are
[`../specs/001-agent-kit-poc/spec.md`](../specs/001-agent-kit-poc/spec.md),
[`plan.md`](../specs/001-agent-kit-poc/plan.md) and
[`tasks.md`](../specs/001-agent-kit-poc/tasks.md).

## 8. Troubleshooting

| Symptom | Fix |
| --- | --- |
| No `agent-kit` tools in Kiro | `agent-kit kiro status`; if incomplete, `agent-kit kiro install`. Ensure `agent-kit` is on the PATH Kiro inherits (`which agent-kit`); otherwise install with `uv tool install '.[openai]'` or set an absolute `command` in `.kiro/settings/mcp.json` |
| Tools error with "Configuration not found" | the project has no `.agent/config.yaml` — run `agent-kit init` or `agent-kit kiro install` inside the project |
| `model.provider: openai` fails | export `OPENAI_API_KEY` in the environment Kiro starts from, or switch to the offline model: `agent-kit config set model.provider mock` |
| Hook never fires | hooks live in `.kiro/hooks/*.json` (v1). Legacy `.kiro.hook` files are ignored by Kiro 1.0 |
| Hook exits non-zero | run the same command in a terminal; the hook is just `agent-kit …` |
| Evaluator says FAIL after a save | read the ✗ lines — a required section is missing; then `agent-kit mcp call agent_kit_evaluate --arguments '{"output_file": "output/sample-001.md"}'` |

## 9. Verified format sources

The generated formats follow the current Kiro documentation:

- Steering — <https://kiro.dev/docs/steering.md> (`inclusion`, `fileMatchPattern`, CLI note)
- Hooks (v1) — <https://kiro.dev/docs/hooks.md>, <https://kiro.dev/docs/hooks/types.md>, <https://kiro.dev/docs/hooks/actions.md>
- Legacy hook migration — <https://kiro.dev/docs/ide/whats-new-v1/hooks.md>
- MCP configuration — <https://kiro.dev/docs/mcp/configuration.md>
- Specs — <https://kiro.dev/docs/specs.md>, <https://kiro.dev/docs/specs/feature-specs.md>, <https://kiro.dev/docs/specs/best-practices.md>
- Custom agents — <https://kiro.dev/docs/custom-agents/creating.md>, <https://kiro.dev/docs/custom-agents/configuration-reference.md>
- Kiro CLI setup — <https://kiro.dev/docs/cli/setup.md>
- Spec Kit's Kiro integration (`.kiro/prompts/speckit.*.md`) — <https://github.com/github/spec-kit>

Because Kiro's formats evolve, the templates live in one place
(`integrations/kiro/`) so a format update is a single edit plus
`tests/unit/test_kiro_integration.py`.
