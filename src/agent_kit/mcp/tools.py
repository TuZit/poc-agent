"""MCP tools backed by the agent-kit runtime.

These are the capabilities an MCP client (Kiro, other IDEs, scripts) can call.
Each handler is a thin wrapper around the same runtime the CLI uses, so an MCP
call and a CLI invocation produce identical results.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent_kit.agent.runtime import AgentRuntime
from agent_kit.config import ConfigError, load_config
from agent_kit.evaluation import REQUIRED_SECTIONS, evaluate_file, evaluate_text
from agent_kit.model import available_providers
from agent_kit.paths import AssetError
from agent_kit.skills import SkillError, SkillLoader
from agent_kit.skills.loader import project_skills_dir
from agent_kit.tools import available_tools, create_enabled_tools
from agent_kit.tools.base import ToolError
from agent_kit.workflow import available_workflows


@dataclass(frozen=True)
class MCPTool:
    """One MCP tool: metadata plus a handler over the project root."""

    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Callable[[dict[str, Any], Path], str]


class MCPToolError(RuntimeError):
    """Raised when a tool cannot execute its request."""


def _require_string(arguments: dict[str, Any], key: str) -> str:
    value = arguments.get(key)
    if not isinstance(value, str) or not value.strip():
        raise MCPToolError(f"'{key}' is required and must be a non-empty string.")
    return value


def _resolve_inside(project_root: Path, relative: str) -> Path:
    """Resolve ``relative`` and refuse to leave the project root."""
    candidate = Path(relative)
    resolved = (
        candidate.resolve() if candidate.is_absolute() else (project_root / candidate).resolve()
    )
    if resolved != project_root and project_root not in resolved.parents:
        raise MCPToolError(f"Path '{relative}' is outside the project root ({project_root}).")
    return resolved


def _concepts(arguments: dict[str, Any]) -> tuple[str, ...]:
    raw = arguments.get("required_concepts") or []
    if isinstance(raw, str):
        return (raw,)
    return tuple(str(item) for item in raw)


# --- handlers -------------------------------------------------------------
def run_workflow(arguments: dict[str, Any], project_root: Path) -> str:
    """Run the configured workflow over inline text or a project file."""
    input_text = arguments.get("input_text")
    input_file = arguments.get("input_file")

    if not input_text and input_file:
        source = _resolve_inside(project_root, str(input_file))
        if not source.is_file():
            raise MCPToolError(f"Input file not found: {input_file}")
        input_text = source.read_text(encoding="utf-8")
    if not input_text:
        raise MCPToolError("Provide 'input_text' or 'input_file'.")

    try:
        config = load_config(project_root)
        runtime = AgentRuntime(config)
    except (ConfigError, ToolError) as exc:
        raise MCPToolError(str(exc)) from exc

    try:
        result = runtime.run_workflow(
            str(input_text),
            workflow_name=arguments.get("workflow"),
            skill_name=arguments.get("skill"),
        )
    except Exception as exc:  # surfaced to the client as an MCP tool error
        raise MCPToolError(f"Workflow failed: {exc}") from exc

    header = [
        f"workflow: {result.workflow}",
        f"valid: {result.valid}",
        f"tool_calls: {result.tool_call_count}",
    ]
    for issue in result.issues:
        header.append(f"issue: {issue}")

    write_to = arguments.get("write_output")
    if isinstance(write_to, str) and write_to.strip():
        destination = _resolve_inside(project_root, write_to)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(result.output, encoding="utf-8")
        header.append(f"written: {destination.relative_to(project_root)}")

    return "\n".join(header) + "\n\n" + result.output


def evaluate(arguments: dict[str, Any], project_root: Path) -> str:
    """Evaluate generated output: inline text, or a file inside the project."""
    concepts = _concepts(arguments)
    output_file = arguments.get("output_file")

    if output_file:
        target = _resolve_inside(project_root, str(output_file))
        result = evaluate_file(
            target, required_sections=REQUIRED_SECTIONS, required_concepts=concepts
        )
    elif arguments.get("text"):
        result = evaluate_text(
            str(arguments["text"]),
            required_sections=REQUIRED_SECTIONS,
            required_concepts=concepts,
        )
    else:
        raise MCPToolError("Provide 'output_file' or 'text'.")

    return result.render()


def workflow_output_schema(arguments: dict[str, Any], project_root: Path) -> str:
    """Return the section structure a workflow output must satisfy."""
    lines = ["Required sections for a valid requirement-analysis output:", ""]
    lines += [f"- {section}" for section in REQUIRED_SECTIONS]
    return "\n".join(lines)


def list_capabilities(arguments: dict[str, Any], project_root: Path) -> str:
    """Describe the resolved configuration and everything the kit can load."""
    lines = [f"project: {project_root}", f"providers: {', '.join(available_providers())}"]
    lines.append(f"tools: {', '.join(available_tools())}")
    lines.append(f"workflows: {', '.join(available_workflows())}")

    loader = SkillLoader(project_root=project_root)
    skills = loader.discover()
    lines.append(f"skills: {', '.join(skills) or '(none)'}")
    local = project_skills_dir(project_root)
    if local.is_dir():
        lines.append(f"project skills dir: {local}")

    try:
        config = load_config(project_root)
    except ConfigError as exc:
        lines.append("")
        lines.append(f"configuration: NOT AVAILABLE — {exc}")
        return "\n".join(lines)

    lines.append("")
    lines.append("configuration:")
    lines.append(f"- agent: {config.agent.name}")
    lines.append(f"- model: {config.model.provider}/{config.model.name}")
    lines.append(f"- enabled tools: {', '.join(config.enabled_tool_names()) or '(none)'}")
    lines.append(f"- skills: {', '.join(config.skills) or '(none)'}")
    lines.append(f"- workflow: {config.workflow.name}")

    try:
        enabled = create_enabled_tools(config.tools, project_root)
        lines.append(f"- resolved tools: {', '.join(tool.name for tool in enabled) or '(none)'}")
    except ToolError as exc:
        lines.append(f"- resolved tools: ERROR — {exc}")

    return "\n".join(lines)


def read_skill(arguments: dict[str, Any], project_root: Path) -> str:
    """Return the Markdown instructions of a skill."""
    name = _require_string(arguments, "name")
    try:
        skill = SkillLoader(project_root=project_root).load(name)
    except (SkillError, AssetError) as exc:
        raise MCPToolError(str(exc)) from exc
    return f"# Skill: {skill.name}\n\n{skill.instructions}"


# --- registry -------------------------------------------------------------
def build_mcp_tools(project_root: Path | None = None) -> list[MCPTool]:
    """All MCP tools exposed by agent-kit (``project_root`` is bound per call)."""
    return [
        MCPTool(
            name="agent_kit_run_workflow",
            description=(
                "Run the configured agent-kit workflow and return the generated Markdown. "
                "Use this to turn a requirement (inline text or a project file) into a "
                "structured requirement summary. Optionally persists the result."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "input_text": {
                        "type": "string",
                        "description": "Requirement text to analyse.",
                    },
                    "input_file": {
                        "type": "string",
                        "description": "Path to a requirement file, relative to the project root.",
                    },
                    "workflow": {
                        "type": "string",
                        "description": "Workflow name (default: the configured workflow).",
                    },
                    "skill": {
                        "type": "string",
                        "description": "Skill name override (default: the configured skill).",
                    },
                    "write_output": {
                        "type": "string",
                        "description": (
                            "Optional path (relative to the project root) to write the output to."
                        ),
                    },
                },
                "anyOf": [{"required": ["input_text"]}, {"required": ["input_file"]}],
                "additionalProperties": False,
            },
            handler=run_workflow,
        ),
        MCPTool(
            name="agent_kit_evaluate",
            description=(
                "Deterministically evaluate a requirement summary: required sections, "
                "non-empty output and optional required concepts. Returns a PASS/FAIL report."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "output_file": {
                        "type": "string",
                        "description": "Output file to evaluate, relative to the project root.",
                    },
                    "text": {
                        "type": "string",
                        "description": "Inline Markdown to evaluate instead of a file.",
                    },
                    "required_concepts": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Keywords that must appear in the output.",
                    },
                },
                "additionalProperties": False,
            },
            handler=evaluate,
        ),
        MCPTool(
            name="agent_kit_capabilities",
            description=(
                "Describe this project's agent-kit setup: providers, tools, skills, "
                "workflows and the resolved .agent/config.yaml."
            ),
            input_schema={"type": "object", "properties": {}, "additionalProperties": False},
            handler=list_capabilities,
        ),
        MCPTool(
            name="agent_kit_read_skill",
            description="Return the Markdown instructions of a named agent-kit skill.",
            input_schema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Skill name, e.g. requirement-analysis.",
                    }
                },
                "required": ["name"],
                "additionalProperties": False,
            },
            handler=read_skill,
        ),
    ]


__all__ = [
    "MCPTool",
    "MCPToolError",
    "build_mcp_tools",
    "evaluate",
    "list_capabilities",
    "read_skill",
    "run_workflow",
    "workflow_output_schema",
]
