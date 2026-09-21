# Requirements Document — Agent Kit POC workspace

## Introduction

This workspace runs the Agent Kit POC: a small, installable agent kit that turns a
raw requirement into a structured requirement summary, evaluates it
deterministically, and exposes the same runtime to Kiro through an MCP server.
These requirements describe the behaviour this workspace must provide.

## Glossary

- **Agent Kit CLI** — the `agent-kit` command line interface (`init`, `doctor`,
  `config`, `run`, `evaluate`, `kiro`, `mcp`).
- **Runtime** — `AgentRuntime`, the assembly of model, tools, skills and workflow.
- **Skill** — a directory containing `SKILL.md` whose Markdown instructions are
  passed to the agent verbatim.
- **Workflow** — a named process (`requirement-analysis`) that combines skill,
  agent, tools and validation.
- **Requirement Summary** — the Markdown output containing Objective, Actors,
  Functional Requirements, Product Attributes, Non-Functional Requirements,
  Assumptions and Open Questions.
- **MCP tool** — a capability exposed over the Model Context Protocol
  (`agent_kit_run_workflow`, `agent_kit_evaluate`, `agent_kit_capabilities`,
  `agent_kit_read_skill`).
- **Evaluator** — the deterministic checker with no LLM judgement.

## Requirements

### Requirement 1: Project initialization and configuration

**User Story:** As a developer, I want a runnable project skeleton and a single
configuration file, so that I can adopt the kit without reading its source.

#### Acceptance Criteria

1. WHEN `agent-kit init <project>` is executed, THE SYSTEM SHALL create
   `.agent/config.yaml`, `README.md` and the sample input/expected files.
2. WHEN the target directory already exists and is not empty and `--force` is not
   supplied, THE SYSTEM SHALL refuse to write and SHALL explain the refusal.
3. WHEN `agent-kit doctor` is executed, THE SYSTEM SHALL report Python version,
   configuration, model configuration, required environment variables, tools,
   skills and workflow, and SHALL exit non-zero if any check fails.
4. WHEN a configuration value must change, THE SYSTEM SHALL allow
   `agent-kit config set <dotted-key> <value>` without editing code.
5. WHERE a secret is required, THE SYSTEM SHALL read it from an environment
   variable and SHALL NOT accept it from `.agent/config.yaml`.

### Requirement 2: Deterministic requirement analysis workflow

**User Story:** As a developer, I want a requirement analysed into a structured
summary, so that downstream design work starts from an agreed contract.

#### Acceptance Criteria

1. WHEN `agent-kit run` is executed in a configured project, THE SYSTEM SHALL load
   the configuration, load the configured skill, initialise the model and the
   enabled tools, execute the configured workflow and write the output file.
2. WHEN the requirement-analysis workflow executes, THE SYSTEM SHALL pass the
   skill instructions to the agent as part of the system context.
3. WHEN the model requests a tool call, THE SYSTEM SHALL execute the tool, feed the
   result back to the model and continue until the model returns a final answer.
4. WHEN the model provider is `mock`, THE SYSTEM SHALL produce output without any
   network access and without an API key.
5. WHEN the generated output is missing a required section, THE SYSTEM SHALL report
   the workflow result as invalid and SHALL name the missing section.
6. WHEN an unknown workflow or skill name is requested, THE SYSTEM SHALL fail with
   the list of available names.

### Requirement 3: Deterministic evaluation

**User Story:** As a maintainer, I want a repeatable regression gate, so that
output quality is checked without an LLM judge.

#### Acceptance Criteria

1. WHEN `agent-kit evaluate <file>` is executed on output containing every required
   section, THE SYSTEM SHALL report `Result: PASS` and exit zero.
2. WHEN a required section is absent, THE SYSTEM SHALL mark that section with `✗`
   and SHALL exit non-zero.
3. WHEN the output file is missing, empty or unreadable, THE SYSTEM SHALL fail the
   "Output generated" check.
4. WHEN `--require-concept <keyword>` is supplied and the keyword is absent, THE
   SYSTEM SHALL fail that concept check.

### Requirement 4: Restricted tool execution

**User Story:** As a security owner, I want the agent's tools bounded, so that a
model-driven tool call cannot damage the machine.

#### Acceptance Criteria

1. WHEN the filesystem tool resolves a path, THE SYSTEM SHALL confine the resolved
   path to the project directory, including after `..` expansion and symlink
   resolution.
2. WHEN the shell tool receives a command outside the whitelist (`python`,
   `pytest`, `git`), THE SYSTEM SHALL refuse to execute it and SHALL report the
   whitelist.
3. WHEN the shell tool executes a permitted command, THE SYSTEM SHALL pass
   arguments as a list without shell interpretation and SHALL apply a timeout.
4. WHEN a tool fails or a boundary is violated, THE SYSTEM SHALL return the failure
   to the model as a tool result and SHALL NOT crash the run.

### Requirement 5: Kiro integration

**User Story:** As a developer working in Kiro, I want agent-kit available as a
native tool with project context and automation, so that spec-driven work and the
agent kit reinforce each other.

#### Acceptance Criteria

1. WHEN `agent-kit init <project> --ai kiro` or `agent-kit kiro install` is
   executed, THE SYSTEM SHALL create `.kiro/steering/`, `.kiro/hooks/`,
   `.kiro/agents/`, `.kiro/prompts/`, `.kiro/settings/mcp.json` and
   `.kiro/specs/agent-kit-poc/`.
2. WHEN the Kiro integration already exists, THE SYSTEM SHALL leave existing files
   unchanged unless `--force` is supplied.
3. WHEN Kiro loads the MCP server, THE SYSTEM SHALL answer `initialize`,
   `tools/list` and `tools/call` over stdio using JSON-RPC 2.0.
4. WHEN an MCP client calls `agent_kit_run_workflow` or `agent_kit_evaluate`, THE
   SYSTEM SHALL produce the same result as the equivalent CLI invocation.
5. WHEN steering is loaded, THE SYSTEM SHALL describe the workspace layout, the
   available MCP tools and the requirement-summary contract.
6. WHEN a hook fires, THE SYSTEM SHALL run the configured `agent-kit` command and
   SHALL report its exit status without blocking the session.
