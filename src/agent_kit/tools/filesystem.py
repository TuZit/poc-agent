"""Filesystem tool — read/write text files, restricted to the project directory.

SECURITY BOUNDARY
-----------------
Every path is resolved against the project root and re-checked *after*
resolution (``Path.resolve()`` follows ``..`` and symlinks), so attempts such
as ``../../etc/passwd`` or a symlink pointing outside the project are rejected.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar

from agent_kit.tools.base import Tool, ToolError, ToolResult


class FilesystemTool(Tool):
    """Read and write UTF-8 text files inside the project."""

    name = "filesystem"
    description = (
        "Read or write a UTF-8 text file. Paths are resolved against the project "
        "root; anything outside the project directory is denied."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["read_file", "write_file"],
                "description": "Operation to perform.",
            },
            "path": {
                "type": "string",
                "description": "File path, relative to the project root.",
            },
            "content": {
                "type": "string",
                "description": "Content to write. Required for write_file.",
            },
        },
        "required": ["action", "path"],
        "additionalProperties": False,
    }

    # -- security boundary -------------------------------------------------
    def resolve_inside_root(self, path: str | Path) -> Path:
        """Resolve ``path`` and enforce the project-directory boundary."""
        candidate = Path(path)
        resolved = (
            candidate.resolve() if candidate.is_absolute() else (self.root / candidate).resolve()
        )
        if resolved != self.root and self.root not in resolved.parents:
            raise ToolError(
                f"Access denied: '{path}' resolves outside the project directory ({self.root})."
            )
        return resolved

    # -- Tool API ----------------------------------------------------------
    def execute(
        self,
        action: str = "",
        path: str = "",
        content: str | None = None,
        **_ignored: Any,
    ) -> ToolResult:
        target = self.resolve_inside_root(path)
        if target == self.root:
            return ToolResult(
                success=False,
                output="'path' must point to a file inside the project, not the project root.",
            )

        if action == "read_file":
            if not target.is_file():
                return ToolResult(success=False, output=f"File not found: {path}")
            try:
                return ToolResult(success=True, output=target.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError) as exc:
                return ToolResult(success=False, output=f"Cannot read {path}: {exc}")

        if action == "write_file":
            if content is None:
                return ToolResult(
                    success=False, output="write_file requires the 'content' argument."
                )
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
            except OSError as exc:
                return ToolResult(success=False, output=f"Cannot write {path}: {exc}")
            return ToolResult(success=True, output=f"Wrote {len(content)} characters to {path}.")

        return ToolResult(
            success=False,
            output=f"Unknown action '{action}'. Supported actions: read_file, write_file.",
        )
