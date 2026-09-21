# Agent Kit POC Constitution

<!--
Sync Impact Report
Version: 1.0.0 | Ratified: 2025-09-21 | Last amended: 2025-09-21
Source: POC_TASK.md §18 (Development Principles)
-->

## Core Principles

### I. Small by Default (POC-first)

The deliverable is a proof of concept, not a platform. Production concerns —
multi-agent orchestration, Kubernetes, RBAC, billing, vector stores, complex
observability — MUST NOT be implemented. Every new file MUST justify itself
against the acceptance criteria in `specs/001-agent-kit-poc/spec.md`.

**Rationale:** the POC exists to validate packaging, configuration and
extensibility, not to run production traffic.

### II. Interfaces Before Implementations

`Model`, `Tool`, `Skill` and `Workflow` are abstract contracts. Concrete
implementations MUST live behind those contracts and MUST be replaceable
without touching the agent loop.

**Rationale:** the agent runtime must survive a provider or tool swap.

### III. Vendor Neutrality

Only modules under `src/agent_kit/model/` MAY import a provider SDK, and those
imports MUST be lazy. No other module may reference a vendor package name.

**Rationale:** adding `AnthropicModel` or `GeminiModel` must be additive.

### IV. Configuration Over Hard-Coding

Behaviour is selected by `.agent/config.yaml`: model provider and name, enabled
tools, loaded skills, workflow. Prompt instructions live in Markdown
(`SKILL.md`), never inside Python string literals.

**Rationale:** the kit is re-targeted per project without code changes.

### V. Security by Default

Tools are restricted by construction: the filesystem tool is anchored to the
project root and re-validates every resolved path; the shell tool accepts an
exact command whitelist (`python`, `pytest`, `git`), passes arguments as a list
with `shell=False`, and applies a timeout. Secrets MUST be environment
variables — never YAML values, never committed files.

**Rationale:** a model-driven tool call is untrusted input.

### VI. Test Without External APIs

The default test path MUST use `MockModel` and MUST pass with no network and no
`OPENAI_API_KEY`. Any test that would require a live provider belongs outside
the default suite.

**Rationale:** `pytest` must be a reliable, hermetic gate.

### VII. Runtime Independent of the CLI

`AgentRuntime` MUST be constructible from a loaded configuration alone. The CLI
is a thin shell: it parses arguments, calls the runtime, prints results and sets
exit codes. The runtime MUST NOT import anything from `agent_kit.cli`.

**Rationale:** the runtime is the product; the CLI is one front end among many
(Kiro, other IDEs, scripts, future services).

### VIII. Extensible Without Implementing

The architecture MUST leave obvious extension points — additional models, tools,
skills, workflows and integrations — while implementing none of them beyond the
POC scope.

**Rationale:** the roadmap is validated by the shape of the seams, not by
shipping the roadmap.

## Additional Constraints

- **Stack:** Python 3.11+, `uv`, Typer, pytest, YAML, Docker.
- **Dependencies:** runtime dependencies stay minimal (`typer`, `pyyaml`);
  provider SDKs are optional extras.
- **Packaging:** assets (skills, templates, samples, integrations) MUST ship
  inside the wheel so an installed CLI works outside the source checkout.
- **Evaluation:** deterministic checks only. No LLM-as-a-judge in the POC.

## Development Workflow

1. Spec (`spec.md`) → 2. Plan (`plan.md`) → 3. Tasks (`tasks.md`) → 4. Implement.
5. After each phase: run `pytest`, fix failures, update documentation, keep the
   code runnable. A phase is not complete until the suite is green.

## Governance

Amendments require a version bump of this document, an update to the affected
spec or plan, and a green test suite. Principle conflicts are resolved in favour
of Principles I and V.

**Version:** 1.0.0 | **Ratified:** 2025-09-21 | **Last amended:** 2025-09-21
