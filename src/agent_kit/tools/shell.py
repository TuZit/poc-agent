"""Shell tool — a strict command whitelist, never a real shell.

SECURITY BOUNDARY
-----------------
1. The executable must be in :data:`DEFAULT_ALLOWED_COMMANDS` (exact match).
2. Arguments are passed as a list with ``shell=False``: no pipes, no ``;``,
   no redirection, no glob expansion, no environment expansion.
3. The process runs with ``cwd`` set to the project root and a timeout, so a
   runaway command cannot hang the agent.
"""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import Any, ClassVar

from agent_kit.tools.base import Tool, ToolResult

#: The entire permitted command surface of the POC.
DEFAULT_ALLOWED_COMMANDS: tuple[str, ...] = ("python", "pytest", "git")


class ShellTool(Tool):
    """Run a whitelisted command inside the project directory."""

    name = "shell"
    description = (
        "Run a whitelisted command inside the project directory. "
        f"Allowed commands: {', '.join(DEFAULT_ALLOWED_COMMANDS)}. "
        "Shell operators, pipes and redirection are not supported."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "enum": list(DEFAULT_ALLOWED_COMMANDS),
                "description": "Whitelisted executable to run.",
            },
            "args": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Argument list, e.g. ['--version'].",
            },
        },
        "required": ["command"],
        "additionalProperties": False,
    }

    def __init__(
        self,
        root: Path | str,
        allowed_commands: Sequence[str] = DEFAULT_ALLOWED_COMMANDS,
        timeout: int = 60,
        **options: Any,
    ) -> None:
        super().__init__(root, **options)
        self.allowed_commands: tuple[str, ...] = tuple(allowed_commands)
        self.timeout = int(timeout)

    def execute(
        self,
        command: str = "",
        args: list[str] | None = None,
        **_ignored: Any,
    ) -> ToolResult:
        arguments = list(args or [])
        if not all(isinstance(argument, str) for argument in arguments):
            return ToolResult(success=False, output="'args' must be a list of strings.")

        # --- security boundary #1: exact whitelist match -------------------
        if command not in self.allowed_commands:
            return ToolResult(
                success=False,
                output=(
                    f"Command '{command}' is not allowed. "
                    f"Whitelist: {', '.join(self.allowed_commands)}."
                ),
            )

        if shutil.which(command) is None:
            return ToolResult(success=False, output=f"Command '{command}' is not on PATH.")

        try:
            # --- security boundary #2: no shell, bounded cwd and time ------
            completed = subprocess.run(
                [command, *arguments],
                cwd=self.root,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                shell=False,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                output=f"Command timed out after {self.timeout}s: {command} {' '.join(arguments)}",
            )
        except OSError as exc:
            return ToolResult(success=False, output=f"Cannot run '{command}': {exc}")

        output = "\n".join(
            part for part in (completed.stdout, completed.stderr) if part and part.strip()
        ).strip()
        if not output:
            output = f"Command finished with exit code {completed.returncode}."
        return ToolResult(success=completed.returncode == 0, output=output)
