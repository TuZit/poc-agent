# Orchestrate: pick the right agents and run them

Let the agent-kit **orchestrator** handle this request.

## Steps

1. If the user's request is not already clear, treat the text supplied with this
   prompt (or the most recent user message) as the request.
2. If you are unsure which agents exist, call `agent_kit_list_agents` first.
3. Call the MCP tool `agent_kit_orchestrate` with:
   - `input_text` (the request) or `input_file` (a path relative to this project),
   - `write_output: "output/sample-orchestration.md"` when the report should be persisted.
4. Read the `selected_agents:` and `strategy:` lines from the result header.
5. Report back: which agents ran, the aggregated report (or its location), and
   `Result: PASS/FAIL` from `agent_kit_evaluate`.

## Rules

- Do not decide the routing yourself when the orchestrator is available — its
  routing is deterministic and explainable.
- Force agents only when the user asks for a specific one:
  `agents: ["code-review"]`, or use `agent_kit_run_workflow` directly.
- Never invent content: unanswered details belong under **Open Questions**.

## CLI equivalent

```bash
agent-kit run --workflow orchestration \
  --input samples/orchestration/input/sample-orchestration.md \
  --output output/sample-orchestration.md
agent-kit evaluate output/sample-orchestration.md --workflow orchestration
```
