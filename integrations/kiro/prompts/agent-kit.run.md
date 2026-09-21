# Run requirement analysis

Use the **agent-kit MCP tool `agent_kit_run_workflow`** to analyse a requirement.

## Steps

1. Identify the requirement to analyse. If the user supplied requirement text or a
   file path with this prompt, use it. Otherwise use
   `samples/requirement-analysis/input/sample-001.md`.
2. Call `agent_kit_read_skill` with `name: "requirement-analysis"` so you follow the
   current skill instructions.
3. Call `agent_kit_run_workflow` with either `input_text` (inline requirement) or
   `input_file` (path relative to this project), plus `write_output:
   "output/sample-001.md"` when the result should be persisted.
4. Call `agent_kit_evaluate` with `output_file: "output/sample-001.md"`.
5. Report the result to the user: the summary itself, the evaluation status, and any
   `issue:` lines from the workflow header.

## Rules

- Do not hand-write the requirement summary when the MCP tool is available.
- Do not report success unless evaluation returns `Result: PASS`.
- Missing information becomes an **Open Questions** entry, never a guess.

## If the tool is unavailable

```bash
agent-kit run --input samples/requirement-analysis/input/sample-001.md --output output/sample-001.md
agent-kit evaluate output/sample-001.md
```
