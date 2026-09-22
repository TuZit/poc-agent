# Unit Test Generation

## Purpose

Derive a unit test plan — and the test cases — for a unit of code.

## Instructions

1. Identify the unit under test and the behaviour it exposes.
2. List the behaviours worth testing, happy path first.
3. List edge cases and failure modes.
4. Choose the test level and the framework the project already uses.
5. State which dependencies must be faked.
6. Produce a structured result.

## Rules

- Return Markdown only: no preamble and no closing commentary.
- Keep the section order of the Output Format below.
- One test case per numbered item, written as `input → expected result`.
- Name tests by behaviour, not by implementation ("raises when stock is negative").
- Never invent behaviour the code does not have — ask under Open Questions.
- If a file is available through the filesystem tool, read it before planning.

## Output Format

Return:

# Unit Test Plan

## Summary

...

## Test Scope

...

## Test Cases

1. ...

## Edge Cases

...

## Open Questions

...

## TODO (team to complete)

> This skill is a skeleton: replace these placeholders with the team's real
> testing standard.

- [ ] Decide whether the agent emits only the plan or also runnable test files
      (and where those files are written).
- [ ] Define the framework conventions per language (pytest, jest, vitest, ...).
- [ ] Define the coverage target and how it is measured.
- [ ] Define naming and structure conventions for generated tests.
- [ ] Add examples of table-driven / parameterised test cases.
