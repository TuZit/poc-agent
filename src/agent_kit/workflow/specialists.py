"""Specialist agent workflows.

Each specialist is one skill plus one output contract. The orchestrator
(:mod:`agent_kit.workflow.orchestration`) selects among them; the CLI, the MCP
tools and Kiro slash commands can also invoke them directly.

Adding a specialist is: a ``SKILL.md`` directory, a subclass here with its
metadata, and one line in :data:`agent_kit.workflow.registry.WORKFLOW_REGISTRY`.
"""

from __future__ import annotations

from agent_kit.workflow.workflow import SkillWorkflow

#: Keyword used when the requirement sample is the default input.
REQUIREMENT_SAMPLE = "samples/requirement-analysis/input/sample-001.md"
CODE_REVIEW_SAMPLE = "samples/code-review/input/sample-code-review.md"
UNIT_TEST_SAMPLE = "samples/unit-test-generation/input/sample-unit-test.md"


class RequirementAnalysisWorkflow(SkillWorkflow):
    """Turn a raw requirement into a structured requirement summary."""

    name = "requirement-analysis"
    title = "Requirement Analysis"
    description = "Turn a raw requirement into a structured requirement summary."
    default_skill = "requirement-analysis"
    required_sections = (
        "Objective",
        "Actors",
        "Functional Requirements",
        "Non-Functional Requirements",
        "Assumptions",
        "Open Questions",
    )
    routing_keywords = (
        "requirement",
        "requirements",
        "user story",
        "specification",
        "acceptance criteria",
        "feature request",
        "business objective",
    )
    default_input = REQUIREMENT_SAMPLE


class CodeReviewWorkflow(SkillWorkflow):
    """Review a code change and report findings."""

    name = "code-review"
    title = "Code Review"
    description = "Review a diff, patch or file and report structured findings."
    default_skill = "code-review"
    required_sections = (
        "Summary",
        "Findings",
        "Recommendations",
        "Open Questions",
    )
    routing_keywords = (
        "code review",
        "review this",
        "review the code",
        "pull request",
        "merge request",
        "diff",
        "patch",
        "refactor",
        "code smell",
        "vulnerability",
        "security issue",
        "bug",
    )
    default_input = CODE_REVIEW_SAMPLE


class UnitTestGenerationWorkflow(SkillWorkflow):
    """Plan (and generate) unit tests for a unit of code."""

    name = "unit-test-generation"
    title = "Unit Test Generation"
    description = "Derive a unit test plan (and test cases) from a unit of code."
    default_skill = "unit-test-generation"
    required_sections = (
        "Summary",
        "Test Scope",
        "Test Cases",
        "Edge Cases",
        "Open Questions",
    )
    routing_keywords = (
        "unit test",
        "unit tests",
        "test case",
        "test cases",
        "test coverage",
        "coverage",
        "pytest",
        "jest",
        "vitest",
        "junit",
        "generate tests",
        "write tests",
        "tests for",
    )
    default_input = UNIT_TEST_SAMPLE


__all__ = [
    "CODE_REVIEW_SAMPLE",
    "REQUIREMENT_SAMPLE",
    "UNIT_TEST_SAMPLE",
    "CodeReviewWorkflow",
    "RequirementAnalysisWorkflow",
    "UnitTestGenerationWorkflow",
]
