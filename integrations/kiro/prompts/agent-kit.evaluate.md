# Evaluate a requirement summary

Validate a generated requirement summary deterministically — no LLM judgement.

## Steps

1. Determine the file to evaluate. If the user named one with this prompt, use it;
   otherwise evaluate `output/sample-001.md`.
2. Call the MCP tool `agent_kit_evaluate` with `output_file` set to that path. Add
   `required_concepts` when the user asks for specific content, e.g.
   `["create product", "search product"]`.
3. Report the full check list and the final `Result: PASS` / `Result: FAIL`.
4. On failure, name every `✗` check and the missing section or concept, then fix the
   summary and evaluate again.

## Rules

- A summary is complete only when every required section passes.
- Section matching is case-insensitive and heading-level agnostic, but section names
  must match the contract in `.kiro/steering/agent-kit-requirements.md`.
- Never edit the evaluator to make output pass; fix the output.

## If the tool is unavailable

```bash
agent-kit evaluate output/sample-001.md
```
