"""Configuration loading for ``.agent/config.yaml``.

Design rules:

* Configuration over hard-coding — model, tools, skills and workflow all come
  from the file, never from Python constants.
* Secrets are environment variables only. The loader records which environment
  variables a provider needs (see :mod:`agent_kit.model`), but never reads or
  stores secret values itself.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

CONFIG_DIR_NAME = ".agent"
CONFIG_FILE_NAME = "config.yaml"


class ConfigError(Exception):
    """Raised when configuration is missing, malformed or invalid."""


def default_config_path(project_root: Path | str = ".") -> Path:
    """Return ``<project_root>/.agent/config.yaml``."""
    return Path(project_root) / CONFIG_DIR_NAME / CONFIG_FILE_NAME


@dataclass(frozen=True)
class AgentSection:
    """Identity of the agent itself."""

    name: str = "poc-agent"


@dataclass(frozen=True)
class ModelSection:
    """Which model provider to use and how to configure it."""

    provider: str = "mock"
    name: str = "mock-model"
    options: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ToolSection:
    """A single tool entry under ``tools:``."""

    enabled: bool = False
    options: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class WorkflowSection:
    """Which workflow to execute and its options."""

    name: str = "requirement-analysis"
    options: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AppConfig:
    """Fully resolved project configuration."""

    agent: AgentSection
    model: ModelSection
    tools: dict[str, ToolSection]
    skills: list[str]
    workflow: WorkflowSection
    project_root: Path
    config_path: Path

    def enabled_tool_names(self) -> list[str]:
        """Names of tools that are switched on, in configuration order."""
        return [name for name, section in self.tools.items() if section.enabled]

    def to_dict(self) -> dict[str, Any]:
        """Serialise back to the YAML shape (used by ``agent-kit config show``)."""
        return {
            "agent": {"name": self.agent.name},
            "model": {
                "provider": self.model.provider,
                "name": self.model.name,
                **self.model.options,
            },
            "tools": {
                name: {"enabled": section.enabled, **section.options}
                for name, section in self.tools.items()
            },
            "skills": list(self.skills),
            "workflow": {"name": self.workflow.name, **self.workflow.options},
        }


def _as_mapping(value: Any, context: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ConfigError(f"{context} must be a YAML mapping.")
    return value


def _passthrough_options(section: dict[str, Any], reserved: set[str]) -> dict[str, Any]:
    """Keys that are not reserved are forwarded to the implementation as options.

    ``options:`` is merged in and wins, so advanced settings can be nested:

        model:
          provider: openai
          name: gpt-4o-mini
          options:
            temperature: 0.2
    """
    extra = {
        key: value
        for key, value in section.items()
        if key not in reserved and key != "options"
    }
    nested = _as_mapping(section.get("options"), "'options'")
    return {**extra, **nested}


def load_config(project_root: Path | str = ".") -> AppConfig:
    """Load and validate ``<project_root>/.agent/config.yaml``.

    Raises:
        ConfigError: with an actionable message when the file is missing,
            unreadable, not YAML, or structurally invalid.
    """
    root = Path(project_root).resolve()
    path = default_config_path(root)

    if not path.is_file():
        raise ConfigError(
            f"Configuration not found at {path}. "
            "Run 'agent-kit init <project>' first, or run the command from the project root."
        )

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML in {path}: {exc}") from exc
    except OSError as exc:
        raise ConfigError(f"Cannot read {path}: {exc}") from exc

    if raw is None:
        raise ConfigError(f"{path} is empty. Expected at least 'model' and 'workflow' sections.")
    if not isinstance(raw, dict):
        raise ConfigError(f"{path} must contain a YAML mapping at the top level.")

    agent_data = _as_mapping(raw.get("agent"), "agent")
    agent = AgentSection(name=str(agent_data.get("name") or "poc-agent"))

    model_data = _as_mapping(raw.get("model"), "model")
    provider = model_data.get("provider")
    if not provider or not isinstance(provider, str):
        raise ConfigError(
            f"model.provider is required in {path} (supported: openai, mock)."
        )
    model_name = model_data.get("name")
    if not model_name or not isinstance(model_name, str):
        raise ConfigError(f"model.name is required in {path} (e.g. 'gpt-4o-mini').")
    model = ModelSection(
        provider=provider.strip().lower(),
        name=model_name.strip(),
        options=_passthrough_options(model_data, {"provider", "name"}),
    )

    tools_data = _as_mapping(raw.get("tools"), "tools")
    tools: dict[str, ToolSection] = {}
    for tool_name, tool_data in tools_data.items():
        entry = _as_mapping(tool_data, f"tools.{tool_name}")
        tools[str(tool_name)] = ToolSection(
            enabled=bool(entry.get("enabled", False)),
            options=_passthrough_options(entry, {"enabled"}),
        )

    skills_raw = raw.get("skills") or []
    if not isinstance(skills_raw, list) or not all(isinstance(item, str) for item in skills_raw):
        raise ConfigError(f"skills must be a list of skill names in {path}.")
    skills = [item.strip() for item in skills_raw if item.strip()]

    workflow_data = _as_mapping(raw.get("workflow"), "workflow")
    workflow_name = workflow_data.get("name")
    if not workflow_name or not isinstance(workflow_name, str):
        raise ConfigError(
            f"workflow.name is required in {path} (e.g. 'requirement-analysis')."
        )
    workflow = WorkflowSection(
        name=workflow_name.strip(),
        options=_passthrough_options(workflow_data, {"name"}),
    )

    return AppConfig(
        agent=agent,
        model=model,
        tools=tools,
        skills=skills,
        workflow=workflow,
        project_root=root,
        config_path=path,
    )


def dump_config(data: dict[str, Any]) -> str:
    """Render a configuration mapping as YAML text."""
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True)
