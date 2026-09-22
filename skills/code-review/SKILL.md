# Code Review

## Purpose

Review a code change (diff, patch or file) and produce a structured code review
report.

## Instructions

1. Identify what changed and why it changed.
2. Check correctness, readability, error handling and security.
3. Check whether the change is covered by tests.
4. Separate blocking issues from suggestions.
5. List the assumptions you had to make.
6. Produce a structured result.

## Rules

- Return Markdown only: no preamble and no closing commentary.
- Keep the section order of the Output Format below.
- Every finding must name the location it refers to (file, function or line).
- Never claim a change is safe without saying what you verified.
- Do not invent code that is not present in the input.
- If a file is available through the filesystem tool, read it instead of guessing.

## Output Format

Return:

# Code Review

## Summary

...

## Findings

1. ...

## Recommendations

...

## Open Questions

...

## TODO (team to complete)

> This skill is a skeleton: replace these placeholders with the team's real
> review standard.

- [ ] Define the severity taxonomy (blocker / major / minor / nit) and how it
      appears in `Findings`.
- [ ] Add language-specific checklists (Python, TypeScript, Java, ...).
- [ ] Define how large a change may be before the agent asks for a split.
- [ ] Define the security checklist (input validation, secrets, injection, authz).
- [ ] Add two or three worked examples of good findings.
