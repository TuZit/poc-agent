# Requirement Analysis

## Purpose

Analyze a software requirement and produce a structured requirement summary.

## Instructions

1. Identify the business objective.
2. Identify actors.
3. Identify functional requirements.
4. Identify non-functional requirements.
5. Identify assumptions.
6. Identify ambiguities.
7. Produce a structured result.

## Rules

- Return Markdown only: no preamble and no closing commentary.
- Keep the section order of the Output Format below.
- Use short, testable statements. One requirement per line.
- Never invent identifiers, prices, SLAs or technologies that the input does not mention.
- When information is missing, record it under Open Questions instead of guessing.
- If a file is available through the filesystem tool, read it before analyzing.

## Output Format

Return:

# Requirement Summary

## Objective

...

## Actors

...

## Functional Requirements

1. ...

## Product Attributes

...

## Non-Functional Requirements

...

## Assumptions

...

## Open Questions

...

## Notes

- `templates/requirement-summary.md` next to this file is the canonical skeleton.
- `agent-kit evaluate <output-file>` checks that every required section exists.
