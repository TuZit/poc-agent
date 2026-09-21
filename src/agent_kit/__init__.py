"""Agent Kit POC — an installable, configuration-driven AI agent kit.

The package is layered so the runtime is usable without the CLI:

    from pathlib import Path

    from agent_kit.agent.runtime import AgentRuntime
    from agent_kit.config import load_config

    runtime = AgentRuntime(load_config(Path(".")))
    result = runtime.run_workflow("Build an e-commerce product management API.")
    print(result.output)

Layers (each one only depends on the layers below it):

    cli  ->  agent.runtime  ->  {model, tools, skills, workflow}  ->  evaluation
"""

__version__ = "0.1.0"

__all__ = ["__version__"]
