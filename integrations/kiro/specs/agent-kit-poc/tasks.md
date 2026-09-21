# Implementation Plan: Agent Kit POC workspace

## Overview

Deliver an installable agent kit: CLI, configuration, layered runtime, one provider
plus a deterministic mock, two restricted tools, one Markdown skill, one workflow,
a deterministic evaluator, tests, Docker support and a Kiro integration. All tasks
below are complete in this workspace.

## Tasks

- [x] 1. Package and scaffold the project
  - [x] 1.1 Create `pyproject.toml` with the `agent-kit` console script and a `[openai]` extra
  - [x] 1.2 Add `.env.example` and `.gitignore` (secrets stay out of the repository)
  - [x] 1.3 Bundle assets into the wheel via hatchling `force-include` and resolve them in `src/agent_kit/paths.py`
    - _Requirements: 1.1_
  - [x] 1.4 Implement `src/agent_kit/scaffold.py` template rendering and copying
    - _Requirements: 1.1, 1.2_

- [x] 2. Implement the CLI
  - [x] 2.1 `agent-kit init` with `--force` and `--ai kiro`
    - _Requirements: 1.1, 1.2, 5.1_
  - [x] 2.2 `agent-kit doctor` with ✓/✗ checks and actionable hints
    - _Requirements: 1.3_
  - [x] 2.3 `agent-kit config show|get|set` over dotted keys
    - _Requirements: 1.4_
  - [x] 2.4 `agent-kit run` and `agent-kit evaluate`
    - _Requirements: 2.1, 3.1_
  - [x] 2.5 Checkpoint — `agent-kit --help` lists every command and `pytest` is green

- [x] 3. Configuration layer
  - [x] 3.1 `load_config` with validation and actionable `ConfigError` messages
    - _Requirements: 1.3, 1.4_
  - [x] 3.2 Pass-through `options:` for providers and tools
    - _Requirements: 1.4_
  - [x] 3.3 Project template `.agent/config.yaml` with the sample input/output
    - _Requirements: 1.1, 1.5_

- [x] 4. Model layer
  - [x] 4.1 `Model` interface plus `Message`, `ToolCall`, `ToolSpec`, `ModelResponse`
    - _Requirements: 2.3, 2.6_
  - [x] 4.2 `MockModel` with deterministic output and scripted replay
    - _Requirements: 2.4_
  - [x] 4.3 `OpenAIModel` with lazy SDK import and environment-based key
    - _Requirements: 1.5, 2.3_
  - [x] 4.4 `MODEL_REGISTRY` and `create_model`
    - _Requirements: 2.6_

- [x] 5. Tool layer
  - [x] 5.1 `Tool` interface and `ToolResult`
    - _Requirements: 4.4_
  - [x] 5.2 `FilesystemTool` confined to the resolved project root
    - _Requirements: 4.1_
  - [x] 5.3 `ShellTool` with the `python`, `pytest`, `git` whitelist, `shell=False` and a timeout
    - _Requirements: 4.2, 4.3_
  - [x] 5.4 Build enabled tools from configuration
    - _Requirements: 1.4, 2.1_

- [x] 6. Skills
  - [x] 6.1 `SKILL.md` for `requirement-analysis` with the output contract
    - _Requirements: 2.2_
  - [x] 6.2 `SkillLoader` discovering project-local then bundled skills, validating existence and non-emptiness
    - _Requirements: 2.2, 2.6_

- [x] 7. Agent and workflow
  - [x] 7.1 Agent loop with tool execution, result feedback and `max_iterations`
    - _Requirements: 2.3, 4.4_
  - [x] 7.2 `AgentState` transcript and tool audit trail
    - _Requirements: 2.3_
  - [x] 7.3 `AgentRuntime` assembling model, tools, skills and workflow from configuration
    - _Requirements: 2.1_
  - [x] 7.4 `requirement-analysis` workflow with section validation
    - _Requirements: 2.1, 2.5_

- [x] 8. Evaluation
  - [x] 8.1 Deterministic checks: existence, non-emptiness, required sections, required concepts
    - _Requirements: 3.1, 3.2, 3.3, 3.4_
  - [x] 8.2 PASS/FAIL rendering and non-zero exit on failure
    - _Requirements: 3.1, 3.2_

- [x] 9. Tests
  - [x] 9.1 Unit tests for configuration, skills, models, tools, agent, workflow, evaluator, scaffold and CLI
    - _Requirements: 2.4, 3.1, 4.1_
  - [x] 9.2 Integration test: `init → config → run → output → evaluate` with `MockModel`
    - _Requirements: 2.4, 3.1_
  - [x] 9.3 Checkpoint — the suite passes with no `OPENAI_API_KEY` and no network

- [x] 10. Docker and documentation
  - [x] 10.1 `Dockerfile` running the installed CLI as a non-root user, with no secrets
    - _Requirements: 1.5_
  - [x] 10.2 `README.md`, `docs/architecture.md`, `docs/development.md`, `docs/kiro-integration.md`
    - _Requirements: 5.5_

- [x] 11. Kiro integration
  - [x] 11.1 Bundled templates under `integrations/kiro/` (steering, hooks, prompts, agent, MCP settings, specs)
    - _Requirements: 5.1, 5.5_
  - [x] 11.2 `install_kiro` / `kiro_status` / `uninstall_kiro` with idempotent installs
    - _Requirements: 5.1, 5.2_
  - [x] 11.3 `agent-kit kiro install|status|uninstall`
    - _Requirements: 5.1_
  - [x] 11.4 Minimal MCP stdio server with `initialize`, `tools/list`, `tools/call`
    - _Requirements: 5.3_
  - [x] 11.5 MCP tools: run workflow, evaluate, capabilities, read skill
    - _Requirements: 5.4_
  - [x] 11.6 Kiro spec artifacts in this workspace and tests for the integration
    - _Requirements: 5.1, 5.6_
  - [x] 11.7 Checkpoint — `agent-kit kiro status` reports a complete integration and the MCP handshake passes
