# {{PROJECT_NAME}}

Project scaffolded by **Agent Kit POC** (`agent-kit init`).

## Quickstart

```bash
agent-kit doctor                       # validate config, model and environment
agent-kit config set model.provider mock   # offline, deterministic model
agent-kit run                          # run the configured workflow
agent-kit evaluate output/sample-001.md
```

## Layout

```text
{{PROJECT_NAME}}/
├── .agent/
│   ├── config.yaml                     # agent, model, tools, skills, workflow
│   └── skills/<skill>/SKILL.md         # optional project-local skill overrides
├── output/                             # generated results (created by `agent-kit run`)
└── samples/requirement-analysis/
    ├── input/sample-001.md             # default input
    └── expected/sample-001.md          # reference output (not an exact match target)
```

## Configuration

`.agent/config.yaml` is the single source of truth. Everything — model provider,
enabled tools, loaded skills and the workflow — is configuration, not code.

Secrets stay in the environment:

```bash
cp /path/to/agent-kit/.env.example .env
set -a && source .env && set +a         # exports OPENAI_API_KEY, ...
```

## Using a real model

```bash
export OPENAI_API_KEY=sk-...
agent-kit config set model.provider openai
agent-kit config set model.name gpt-4o-mini
agent-kit run --input samples/requirement-analysis/input/sample-001.md
```

## Using Kiro

```bash
agent-kit kiro install     # .kiro steering + hooks + MCP server registration
```

Then open the project in Kiro: the agent-kit MCP tools are available as
`agent-kit` tools, the steering file explains the workflow, and the hooks can
run `agent-kit evaluate` automatically.

## Adding your own skill

```bash
mkdir -p .agent/skills/my-skill
$EDITOR .agent/skills/my-skill/SKILL.md     # Markdown instructions
agent-kit config set skills.0 my-skill
```

Project-local skills take precedence over the ones shipped with agent-kit.
