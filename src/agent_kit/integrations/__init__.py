"""Editor / agent-tool integrations shipped with agent-kit.

An integration writes the files one AI coding tool reads from a project:
instruction or steering files, MCP server registration, prompt/command files,
hooks and (for Kiro) spec artifacts.

**This phase ships Kiro only.** The framework underneath is generic, so adding
another tool later is:

1. add templates under ``integrations/<name>/``,
2. add a :class:`~agent_kit.integrations.base.TemplateIntegration` subclass,
3. register an instance in :data:`INTEGRATION_REGISTRY`.

The CLI (``agent-kit init --integration <name>`` and
``agent-kit integration install <name>``) then supports it automatically.
See ``docs/agent-integrations.md`` for the seam and the verified file paths of
other tools.
"""

from __future__ import annotations

from collections.abc import Sequence

from agent_kit.integrations.base import (
    IntegrationError,
    IntegrationStatus,
    TemplateIntegration,
    install_many,
    parse_integration_names,
)
from agent_kit.integrations.kiro import (
    KIRO,
    KIRO_DIR_NAME,
    KIRO_SPEC_NAME,
    KiroIntegration,
    expected_kiro_files,
    install_kiro,
    kiro_status,
    uninstall_kiro,
)

#: Registry of available integrations, keyed by the name used on the CLI.
#:
#: Kiro is the supported integration for this phase. The registry exists so that
#: adding another agent tool later is a template directory plus one line here —
#: no CLI, runtime or packaging changes (see docs/agent-integrations.md).
INTEGRATION_REGISTRY: dict[str, TemplateIntegration] = {
    integration.name: integration for integration in (KIRO,)
}


def available_integrations() -> list[str]:
    """Names accepted by ``--integration``."""
    return sorted(INTEGRATION_REGISTRY)


def get_integration(name: str) -> TemplateIntegration:
    """Look up one integration by name."""
    integration = INTEGRATION_REGISTRY.get(name.strip().lower())
    if integration is None:
        raise IntegrationError(
            f"Unknown integration '{name}'. Available integrations: "
            f"{', '.join(available_integrations())}."
        )
    return integration


def resolve_integrations(values: str | Sequence[str] | None) -> list[TemplateIntegration]:
    """Resolve CLI input (``"kiro,claude"``, repeated flags, ...) to instances."""
    return [get_integration(name) for name in parse_integration_names(values)]


def integration_descriptions() -> list[tuple[str, str, str]]:
    """``(name, title, description)`` for every integration, sorted by name."""
    return [
        (name, INTEGRATION_REGISTRY[name].title, INTEGRATION_REGISTRY[name].description)
        for name in available_integrations()
    ]


__all__ = [
    "INTEGRATION_REGISTRY",
    "KIRO",
    "KIRO_DIR_NAME",
    "KIRO_SPEC_NAME",
    "IntegrationError",
    "IntegrationStatus",
    "KiroIntegration",
    "TemplateIntegration",
    "available_integrations",
    "expected_kiro_files",
    "get_integration",
    "install_kiro",
    "install_many",
    "integration_descriptions",
    "kiro_status",
    "parse_integration_names",
    "resolve_integrations",
    "uninstall_kiro",
]
