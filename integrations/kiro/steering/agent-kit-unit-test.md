---
inclusion: fileMatch
fileMatchPattern: ["samples/unit-test-generation/**/*.md", "output/sample-unit-test.md", "output/test-*.md"]
---

# Unit test plan contract

Every unit test plan MUST contain these sections, in this order and with these
exact headings:

1. `# Unit Test Plan`
2. `## Summary` — what unit is covered and the testing approach.
3. `## Test Scope` — in scope and explicitly out of scope.
4. `## Test Cases` — numbered, written as `input → expected result`.
5. `## Edge Cases` — boundaries, invalid input, empty input, large values.
6. `## Open Questions` — behaviour that is unclear and must be confirmed.

## Style

- Name tests by behaviour, not by implementation details.
- One assertion per case; state the fixture or fake needed.
- Never invent behaviour the code does not have — ask instead.
- Verify with the MCP tool `agent_kit_evaluate` (`--workflow unit-test-generation`) or:

```bash
agent-kit evaluate output/sample-unit-test.md --workflow unit-test-generation
```

A plan is only complete when that command reports `Result: PASS`.
