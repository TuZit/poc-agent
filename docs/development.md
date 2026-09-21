# Development guide

## 1. Local setup

```bash
uv python install 3.12        # if you do not have Python 3.11+
uv sync --all-extras          # .venv with typer, pyyaml, pytest, openai
uv run agent-kit --help
```

Without `uv`:

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e '.[openai]' pytest
```

## 2. Running tests

```bash
uv run pytest                       # everything (offline, no API key)
uv run pytest tests/unit -q         # unit only
uv run pytest tests/integration -v  # end-to-end flow
uv run pytest -k kiro               # Kiro integration
uv run pytest -k mcp                # MCP server
```

The suite must stay hermetic: any test that needs network or `OPENAI_API_KEY`
does not belong in the default run. `MockModel` (deterministic output, scripted
replay) is how that is achieved — see `tests/unit/test_agent.py` for tool-loop
tests and `tests/integration/test_end_to_end.py` for the full flow.

## 3. Manual smoke test

```bash
uv tool install . --force
cd /tmp && rm -rf agent-kit-demo && agent-kit init agent-kit-demo --ai kiro
cd agent-kit-demo
agent-kit config set model.provider mock
agent-kit doctor                 # expect: Agent environment is ready.
agent-kit run                    # writes output/sample-001.md
agent-kit evaluate output/sample-001.md   # expect: Result: PASS
agent-kit kiro status            # expect: Kiro integration is complete.
agent-kit mcp tools
```

## 4. Demo checklist (POC_TASK §20)

| Step | Command | Expected |
| --- | --- | --- |
| 1 | `uv tool install .` | `agent-kit` on PATH |
| 2 | `agent-kit init demo-project && cd demo-project` | `.agent/config.yaml`, `README.md`, `samples/` |
| 3 | `agent-kit config set model.provider openai` (+ `OPENAI_API_KEY`) | config updated |
| 4 | `agent-kit run` | processes `samples/requirement-analysis/input/sample-001.md` |
| 5 | — | produces `output/sample-001.md` |
| 6 | `agent-kit evaluate output/sample-001.md` | `Evaluation Result: PASS` |
| 7 | `docker build -t agent-kit-poc .` | image builds |
| 8 | `agent-kit kiro install` | `.kiro/` complete; `agent-kit kiro status` exits 0 |

## 5. Adding a component

### Model

```python
# src/agent_kit/model/anthropic.py
from agent_kit.model.base import Message, Model, ModelError, ModelResponse, ToolSpec


class AnthropicModel(Model):
    provider = "anthropic"
    required_env_vars = ("ANTHROPIC_API_KEY",)

    def generate(self, messages: list[Message], tools: list[ToolSpec] | None = None) -> ModelResponse:
        ...  # import the SDK lazily, inside the call
```

Register it in `model/__init__.py`'s `MODEL_REGISTRY`. `doctor` picks up
`required_env_vars` automatically, and the agent needs no change.

### Tool

```python
# src/agent_kit/tools/http.py
from agent_kit.tools.base import Tool, ToolResult


class HttpTool(Tool):
    name = "http"
    description = "Fetch a URL."
    parameters = {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}

    def execute(self, url: str = "", **_: object) -> ToolResult:
        ...
```

Register it in `tools/__init__.py`'s `TOOL_REGISTRY`, then enable it:

```bash
agent-kit config set tools.http.enabled true
```

Add a unit test asserting the security boundary you claim (see
`tests/unit/test_tools.py` for the path-escape and whitelist patterns).

### Skill

```bash
mkdir -p .agent/skills/api-review
cat > .agent/skills/api-review/SKILL.md <<'EOF'
# API Review

## Purpose
Review an API specification.

## Instructions
1. Identify the endpoints.
2. Check request/response schemas.
3. List security gaps.
EOF
agent-kit config set skills.0 api-review
```

No Python involved. A project-local skill with the same name as a bundled skill
wins, which is how a project customises `requirement-analysis`.

### Workflow

Subclass `Workflow`, set `name` and `default_skill`, implement `execute`, and add
it to `WORKFLOW_REGISTRY` in `src/agent_kit/workflow/workflow.py`. Validate the
output with `find_missing_sections` (or any other deterministic check) before
returning `WorkflowResult`.

## 6. Debugging

| Symptom | Start here |
| --- | --- |
| `Configuration not found` | run from the project root or pass `--project` |
| `OPENAI_API_KEY is not set` | export it, or `agent-kit config set model.provider mock` |
| `openai package is not installed` | `uv tool install 'agent-kit-poc[openai]' --force` |
| `Skill 'x' not found` | the error lists search paths and available skills |
| Workflow output invalid | the `run` output lists each missing section |
| Kiro shows no tools | `agent-kit kiro status`; check `agent-kit` is on Kiro's PATH |
| MCP server silent | protocol frames go to stdout, diagnostics to stderr — never `print()` to stdout in `mcp/` |

Useful environment variables: `OPENAI_API_KEY`, `OPENAI_BASE_URL`.

## 7. Code conventions

- Python 3.11+ typing (`X | None`, built-in generics); `from __future__ import
  annotations` in every module.
- Dataclasses for data, ABCs for contracts, registries for pluggability.
- Errors: domain exceptions (`ConfigError`, `SkillError`, `ToolError`,
  `ModelError`, `WorkflowError`, `AgentError`) with actionable messages; the CLI
  converts them into exit code 1.
- Docstrings explain *why*, not *what*; the constitution in
  `.specify/memory/constitution.md` is the tie-breaker for design questions.

## 8. Keeping docs honest

When behaviour changes, update in the same change: `README.md`, the relevant file
in `docs/`, `specs/001-agent-kit-poc/tasks.md`, and the Kiro templates under
`integrations/kiro/` if the integration is affected. The Kiro artifacts and the
repo specs describe the same system in two formats — keep them consistent.
