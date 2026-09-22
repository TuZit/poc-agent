# Code review

Run the **code-review** agent over a diff, patch or file.

## Steps

1. Identify the change to review: the diff the user pasted, a file path, or
   `samples/code-review/input/sample-code-review.md` by default.
2. Call `agent_kit_read_skill` with `name: "code-review"` so you follow the
   current review standard.
3. Call `agent_kit_run_workflow` with:
   - `workflow: "code-review"`,
   - `input_text` or `input_file`,
   - `write_output: "output/sample-code-review.md"` to persist the report.
4. Validate with `agent_kit_evaluate` (`output_file`, `workflow: "code-review"`).
5. Report: the findings that block the merge first, then the suggestions, then the
   open questions.

## Rules

- Findings must name their location and the risk they carry.
- Separate blockers from nits — never bury a blocker.
- Do not invent code that is not in the input.
- Only report success when evaluation returns `Result: PASS`.

## CLI equivalent

```bash
agent-kit run --workflow code-review --input samples/code-review/input/sample-code-review.md
agent-kit evaluate output/sample-code-review.md --workflow code-review
```
