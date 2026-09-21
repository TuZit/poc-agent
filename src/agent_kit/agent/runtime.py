"""Runtime assembly — the entry point that does not depend on the CLI.

    from pathlib import Path

    from agent_kit.agent.runtime import AgentRuntime
    from agent_kit.config import load_config

    runtime = AgentRuntime(load_config(Path(".")))
    result = runtime.run_workflow("Build an e-commerce product management API.")
    print(result.output, result.valid)

Everything the CLI does is composed from this class, which keeps
``CLI -> Runtime -> {Model, Tools, Skills, Workflow}`` a one-way dependency.
"""

from __future__ import annotations

from pathlib import Path

from agent_kit.agent.agent import BASE_SYSTEM_PROMPT, Agent
from agent_kit.config.loader import AppConfig
from agent_kit.model import Model, create_model
from agent_kit.skills.base import Skill
from agent_kit.skills.loader import SkillLoader
from agent_kit.tools import create_enabled_tools
from agent_kit.tools.base import Tool
from agent_kit.workflow.workflow import (
    Workflow,
    WorkflowContext,
    WorkflowResult,
    create_workflow,
)


class AgentRuntime:
    """Builds model, tools and skills from configuration, then runs workflows."""

    def __init__(self, config: AppConfig, project_root: Path | str | None = None) -> None:
        self.config = config
        self.project_root = Path(project_root or config.project_root).resolve()
        self.model: Model = create_model(config.model)
        self.tools: list[Tool] = create_enabled_tools(config.tools, self.project_root)
        self.skill_loader = SkillLoader(project_root=self.project_root)

    # -- composition -------------------------------------------------------
    def load_skill(self, name: str) -> Skill:
        return self.skill_loader.load(name)

    def load_configured_skills(self) -> list[Skill]:
        return self.skill_loader.load_all(self.config.skills)

    def build_agent(self, system_prompt: str | None = None) -> Agent:
        return Agent(
            model=self.model,
            tools=self.tools,
            system_prompt=system_prompt
            or BASE_SYSTEM_PROMPT.format(agent_name=self.config.agent.name),
        )

    def describe(self) -> str:
        skills = ", ".join(self.config.skills) or "(none)"
        tools = ", ".join(tool.name for tool in self.tools) or "(none)"
        return (
            f"agent={self.config.agent.name} model={self.model.describe()} "
            f"tools={tools} skills={skills} workflow={self.config.workflow.name}"
        )

    # -- execution ---------------------------------------------------------
    def run_workflow(
        self,
        input_text: str,
        workflow_name: str | None = None,
        skill_name: str | None = None,
    ) -> WorkflowResult:
        """Execute a workflow over ``input_text``."""
        workflow: Workflow = create_workflow(workflow_name or self.config.workflow.name)

        skill: Skill | None = None
        if skill_name:
            skill = self.load_skill(skill_name)
        elif self.config.skills:
            skill = self.load_skill(self.config.skills[0])
        elif workflow.default_skill:
            skill = self.load_skill(workflow.default_skill)

        context = WorkflowContext(
            input_text=input_text,
            project_root=self.project_root,
            skill=skill,
            workflow_options=dict(self.config.workflow.options),
        )
        return workflow.execute(context, self)
