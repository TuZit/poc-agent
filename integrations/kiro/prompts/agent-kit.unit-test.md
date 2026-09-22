# Unit test plan

Run the **unit-test-generation** agent over a unit of code.

## Steps

1. Identify the unit under test: the code the user pasted, a file path, or
   `samples/unit-test-generation/input/sample-unit-test.md` by default.
2. Call `agent_kit_read_skill` with `name: "unit-test-generation"`.
3. Call `agent_kit_run_workflow` with:
   - `workflow: "unit-test-generation"`,
   - `input_text` or `input_file`,
   - `write_output: "output/sample-unit-test.md"` to persist the plan.
4. Validate with `agent_kit_evaluate` (`output_file`, `workflow: "unit-test-generation"`).
5. Report: the test cases first, then the edge cases, then the open questions.

## Rules

- One test case per line, written as `input → expected result`.
- Name tests by behaviour, not by implementation.
- Never invent behaviour the code does not have — ask instead.
- Only report success when evaluation returns `Result: PASS`.

## CLI equivalent

```bash
agent-kit run --workflow unit-test-generation \
  --input samples/unit-test-generation/input/sample-unit-test.md
agent-kit evaluate output/sample-unit-test.md --workflow unit-test-generation
```
