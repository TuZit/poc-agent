# Tasks: Agent Kit POC

**Feature branch:** `001-agent-kit-poc` · **Spec:** [`spec.md`](spec.md) · **Plan:** [`plan.md`](plan.md)

All tasks are complete. `[P]` marks work that can be done in parallel with its
siblings. Each task lists the files it touches.

## Phase 1 — Project setup

- [x] **T001** Create the package metadata, console script and dependency groups — `pyproject.toml`
- [x] **T002** [P] Add environment template and ignore rules (secrets never committed) — `.env.example`, `.gitignore`, `.dockerignore`
- [x] **T003** [P] Implement bundled-asset resolution with an installed-vs-checkout fallback — `src/agent_kit/paths.py`
- [x] **T004** Implement template rendering and project scaffolding — `src/agent_kit/scaffold.py`
- [x] **T005** Configure pytest for the `tests/` tree — `pyproject.toml`

**Checkpoint A:** `uv sync` succeeds and `uv run pytest` collects tests.

## Phase 2 — Configuration

- [x] **T006** Load and validate `.agent/config.yaml` into `AppConfig` — `src/agent_kit/config/loader.py`
- [x] **T007** Forward unknown/`options:` keys to implementations — `src/agent_kit/config/loader.py`
- [x] **T008** [P] Ship the project template configuration with placeholders — `templates/project/.agent/config.yaml`
- [x] **T009** [P] Ship the template README — `templates/project/README.md`
- [x] **T010** Unit-test valid, malformed, empty and incomplete configuration — `tests/unit/test_config_loader.py`

## Phase 3 — Model layer

- [x] **T011** Define `Model`, `Message`, `ToolCall`, `ToolSpec`, `ModelResponse` — `src/agent_kit/model/base.py`
- [x] **T012** Implement the deterministic `MockModel` with scripted replay — `src/agent_kit/model/mock.py`
- [x] **T013** Implement `OpenAIModel` with lazy SDK import and env-based key — `src/agent_kit/model/openai.py`
- [x] **T014** Add `MODEL_REGISTRY`, `create_model`, `required_env_vars` — `src/agent_kit/model/__init__.py`
- [x] **T015** Unit-test determinism, script replay, SDK mapping (fake client) and missing key — `tests/unit/test_model.py`

**Checkpoint B:** the agent can generate output with no API key.

## Phase 4 — Tools

- [x] **T016** Define `Tool`, `ToolResult`, `ToolError` — `src/agent_kit/tools/base.py`
- [x] **T017** Implement `FilesystemTool` with a resolve-then-validate root boundary — `src/agent_kit/tools/filesystem.py`
- [x] **T018** Implement `ShellTool` with the `python, pytest, git` whitelist, `shell=False` and a timeout — `src/agent_kit/tools/shell.py`
- [x] **T019** Build enabled tools from configuration — `src/agent_kit/tools/__init__.py`
- [x] **T020** Unit-test traversal, absolute paths, whitelist rejection and metacharacter inertness — `tests/unit/test_tools.py`

## Phase 5 — Skills

- [x] **T021** Define `Skill` — `src/agent_kit/skills/base.py`
- [x] **T022** Implement `SkillLoader` with project-over-bundled precedence and validation — `src/agent_kit/skills/loader.py`
- [x] **T023** Write the `requirement-analysis` skill and its template — `skills/requirement-analysis/SKILL.md`, `skills/requirement-analysis/templates/requirement-summary.md`
- [x] **T024** Unit-test loading, precedence, discovery, missing and empty skills — `tests/unit/test_skill_loader.py`

## Phase 6 — Agent runtime

- [x] **T025** Implement the transcript state and tool audit trail — `src/agent_kit/agent/state.py`
- [x] **T026** Implement the model ⇄ tool loop with `max_iterations` and failure recovery — `src/agent_kit/agent/agent.py`
- [x] **T027** Implement `AgentRuntime` assembly from configuration — `src/agent_kit/agent/runtime.py`
- [x] **T028** Unit-test tool round-trip, unknown tool, boundary violation, iteration limit, transcript — `tests/unit/test_agent.py`

## Phase 7 — Workflow

- [x] **T029** Define `Workflow`, `WorkflowContext`, `WorkflowResult`, registry — `src/agent_kit/workflow/workflow.py`
- [x] **T030** Implement `requirement-analysis` with section validation — `src/agent_kit/workflow/workflow.py`
- [x] **T031** Unit-test valid output, missing sections, skill resolution and tool usage — `tests/unit/test_workflow.py`

## Phase 8 — Evaluation

- [x] **T032** Implement heading extraction and deterministic checks — `src/agent_kit/evaluation/evaluator.py`
- [x] **T033** Render the ✓/✗ report and support file/text evaluation — `src/agent_kit/evaluation/evaluator.py`
- [x] **T034** Unit-test sections, concepts, empty and missing files, rendering — `tests/unit/test_evaluator.py`
- [x] **T035** [P] Ship the sample input and expected output — `samples/requirement-analysis/{input,expected}/sample-001.md`

## Phase 9 — CLI

- [x] **T036** Wire the Typer application, `--version` and sub-command registration — `src/agent_kit/cli/main.py`
- [x] **T037** Implement `init` (`--force`, `--ai kiro`) — `src/agent_kit/cli/init.py`
- [x] **T038** Implement `doctor` with actionable hints and exit codes — `src/agent_kit/cli/doctor.py`
- [x] **T039** Implement `config show|get|set` over dotted keys — `src/agent_kit/cli/config.py`
- [x] **T040** Implement `run` (defaults, overrides, output writing, validation) — `src/agent_kit/cli/run.py`
- [x] **T041** Implement `evaluate` (sections and concepts, exit codes) — `src/agent_kit/cli/evaluate.py`
- [x] **T042** Unit-test every command including failure paths — `tests/unit/test_cli.py`

**Checkpoint C:** `agent-kit init → config → run → evaluate` works by hand.

## Phase 10 — Integration test

- [x] **T043** End-to-end test `init → config → run → output → evaluate` with `MockModel` — `tests/integration/test_end_to_end.py`
- [x] **T044** [P] Compare generated sections against the sample expectation — `tests/integration/test_end_to_end.py`
- [x] **T045** [P] Prove a tool-using run and CLI-free runtime usage — `tests/integration/test_end_to_end.py`

**Checkpoint D:** `uv run pytest` is green with no `OPENAI_API_KEY`.

## Phase 11 — MCP server

- [x] **T046** Implement JSON-RPC 2.0 stdio transport and dispatch — `src/agent_kit/mcp/server.py`
- [x] **T047** Implement the four runtime-backed tools with path confinement — `src/agent_kit/mcp/tools.py`
- [x] **T048** Add `agent-kit mcp serve|tools|call` — `src/agent_kit/cli/mcp.py`
- [x] **T049** Unit-test handshake, tool listing, tool calls, errors, transport — `tests/unit/test_mcp_server.py`

## Phase 12 — Kiro integration

- [x] **T050** Author the Kiro templates: steering (always + fileMatch) — `integrations/kiro/steering/*.md`
- [x] **T051** [P] Author the v1 hooks with command actions — `integrations/kiro/hooks/*.json`
- [x] **T052** [P] Author the MCP settings registering `agent-kit mcp serve` — `integrations/kiro/settings/mcp.json`
- [x] **T053** [P] Author the custom Kiro agent bound to the MCP tools — `integrations/kiro/agents/agent-kit.json`
- [x] **T054** [P] Author the file-based prompts — `integrations/kiro/prompts/agent-kit.*.md`
- [x] **T055** [P] Author the Kiro spec artifacts (EARS requirements, design, tasks) — `integrations/kiro/specs/agent-kit-poc/*.md`
- [x] **T056** Implement `install_kiro`/`kiro_status`/`uninstall_kiro` with idempotent installs and generated spec id — `src/agent_kit/integrations/kiro.py`
- [x] **T057** Add `agent-kit kiro install|status|uninstall` — `src/agent_kit/cli/kiro.py`
- [x] **T058** Unit-test layout, formats, idempotence, uninstall and CLI — `tests/unit/test_kiro_integration.py`

**Checkpoint E:** `agent-kit kiro status` exits 0 and the MCP handshake succeeds.

## Phase 13 — Packaging, docs, Docker

- [x] **T059** Force-include assets into the wheel and verify an installed CLI resolves them — `pyproject.toml`
- [x] **T060** Generate and commit the dependency lock file — `uv.lock`
- [x] **T061** Write the Dockerfile (non-root, no secrets) — `Dockerfile`
- [x] **T062** [P] Write the README (what, architecture, install, config, run, test, Docker, extension guides) — `README.md`
- [x] **T063** [P] Write the architecture document — `docs/architecture.md`
- [x] **T064** [P] Write the development guide — `docs/development.md`
- [x] **T065** [P] Write the Kiro integration guide — `docs/kiro-integration.md`
- [x] **T066** Record the governing principles — `.specify/memory/constitution.md`
- [x] **T067** [P] Write the Vietnamese UAT tutorial (install, usage, 35 acceptance cases) — `docs/uat-tutorial.md`
- [x] **T068** [P] Write the packaging & deployment guide (wheel, assets, Docker, CI/CD, secrets, rollback) — `docs/packaging-deployment.md`
- [x] **T069** Make the version single-sourced from `agent_kit.__version__` — `pyproject.toml`, `src/agent_kit/__init__.py`
- [x] **T070** Support `AGENT_KIT_MODEL` as the model-name fallback for deployments — `src/agent_kit/config/loader.py`, `tests/unit/test_config_loader.py`

## Phase 14 — End-user packaging (no Python) & integration registry

- [x] **T071** Freeze a standalone binary with PyInstaller (assets bundled, `sys._MEIPASS` aware) — `packaging/agent-kit.spec`, `packaging/entrypoint.py`, `src/agent_kit/paths.py`
- [x] **T072** Build script producing per-platform artifacts — `scripts/build-binary.sh`
- [x] **T073** One-line installers for macOS/Linux and Windows — `packaging/install.sh`, `packaging/install.ps1`
- [x] **T074** Verify the binary runs with an empty environment (`env -i`, no Python) including `init --ai kiro`, `run`, `evaluate`, `kiro status`, MCP handshake — `docs/end-user-install.md` §7.2
- [x] **T075** Generalise integrations into a registry (`TemplateIntegration`, `INTEGRATION_REGISTRY`) with Kiro as the only registered tool this phase — `src/agent_kit/integrations/base.py`, `src/agent_kit/integrations/__init__.py`
- [x] **T076** Add `agent-kit integration list|install|status|uninstall` and the `--integration/--ai` flag; keep `agent-kit kiro ...` as an alias — `src/agent_kit/cli/integration.py`, `src/agent_kit/cli/kiro.py`, `src/agent_kit/cli/init.py`, `src/agent_kit/cli/main.py`
- [x] **T077** Unit-test the registry contract, name parsing, lifecycle and CLI — `tests/unit/test_integration_registry.py`
- [x] **T078** [P] Write the end-user installation guide (binary/Docker/dev) — `docs/end-user-install.md`
- [x] **T079** [P] Write the agent-integration guide with the seam and verified formats for future tools (Claude Code, Copilot, Codex) — `docs/agent-integrations.md`

**Checkpoint F:** `uv tool install .` then the demo checklist in
[`../../docs/development.md`](../../docs/development.md) passes.

## Dependencies between phases

```text
Phase 1 ─► Phase 2 ─► Phase 3 ─► Phase 4 ─► Phase 5
                                        │
                                        ▼
                     Phase 6 ─► Phase 7 ─► Phase 8 ─► Phase 9
                                        │
                                        ▼
                     Phase 10 (integration) ─► Phase 11 (MCP) ─► Phase 12 (Kiro)
                                        │
                                        ▼
                                  Phase 13 (packaging/docs/Docker)
```

## Verification summary

| Command | Result |
| --- | --- |
| `uv run pytest` | 188 passed, offline, no API key |
| `agent-kit doctor` (mock provider) | `Agent environment is ready.` |
| `agent-kit run` + `agent-kit evaluate output/sample-001.md` | `Result: PASS` |
| `agent-kit kiro status` | `Kiro integration is complete.` |
| Binary with `env -i` (no Python) | `--version`, `init --ai kiro`, `run`, `evaluate` PASS, MCP handshake OK |
| `agent-kit integration list` | only `kiro` registered (this phase) |
| MCP `initialize` / `tools/list` / `tools/call` over stdio | 4 tools listed, calls return runtime results |
