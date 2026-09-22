---
inclusion: fileMatch
fileMatchPattern: ["samples/code-review/**/*.md", "output/sample-code-review.md", "output/review-*.md"]
---

# Code review contract

Every code review report MUST contain these sections, in this order and with
these exact headings:

1. `# Code Review`
2. `## Summary` — what changed and the overall verdict, two or three sentences.
3. `## Findings` — numbered, each one naming its location and the risk it carries.
4. `## Recommendations` — numbered, one actionable change per finding group.
5. `## Open Questions` — anything that needs a human decision.

## Style

- Findings state the problem and the consequence, not just the rule.
- Separate blocking issues from suggestions; never bury a blocker in a list of nits.
- Do not invent code that is not in the input; say what you verified.
- Verify with the MCP tool `agent_kit_evaluate` (`--workflow code-review`) or:

```bash
agent-kit evaluate output/sample-code-review.md --workflow code-review
```

A review is only complete when that command reports `Result: PASS`.
