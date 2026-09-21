---
inclusion: fileMatch
fileMatchPattern: ["samples/**/*.md", "output/**/*.md", "specs/**/*.md", ".kiro/specs/**/*.md"]
---

# Requirement summary contract

Every requirement summary produced in this workspace MUST contain the following
sections, in this order and with these exact headings:

1. `# Requirement Summary`
2. `## Objective` — the business objective, one or two sentences.
3. `## Actors` — `- <actor>: <what they do with the system>`.
4. `## Functional Requirements` — numbered, one testable requirement per line.
5. `## Product Attributes` — the data the requirement describes.
6. `## Non-Functional Requirements` — performance, security, compliance, usability.
7. `## Assumptions` — what the analysis depends on.
8. `## Open Questions` — every ambiguity the input leaves open.

## Style

- Short, testable statements in the imperative: "Create product", not "products could be created".
- Do not invent identifiers, prices, SLAs or technologies the input does not mention.
- If a detail is missing, ask under **Open Questions** instead of guessing.
- Verify with the MCP tool `agent_kit_evaluate`, or from a terminal:

```bash
agent-kit evaluate output/sample-001.md
```

A summary is only complete when that command reports `Result: PASS`.
