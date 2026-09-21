"""Minimal Model Context Protocol server (JSON-RPC 2.0 over stdio).

Implemented directly on the standard library — the POC deliberately avoids an
MCP ecosystem dependency. Supported methods:

* ``initialize`` / ``notifications/initialized``
* ``ping``
* ``tools/list`` / ``tools/call``
* ``resources/list`` / ``prompts/list`` (empty, so clients probe successfully)

stdout carries protocol frames only; diagnostics go to stderr.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import IO, Any

from agent_kit import __version__
from agent_kit.mcp.tools import MCPTool, build_mcp_tools

SERVER_NAME = "agent-kit"
#: Protocol revisions this server understands; the newest is advertised by default.
SUPPORTED_PROTOCOL_VERSIONS: tuple[str, ...] = (
    "2025-06-18",
    "2025-03-26",
    "2024-11-05",
)
DEFAULT_PROTOCOL_VERSION = SUPPORTED_PROTOCOL_VERSIONS[0]

PARSE_ERROR = -32700
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603


class MCPError(Exception):
    """JSON-RPC level error."""

    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = code


class MCPServer:
    """Serves agent-kit capabilities to any MCP client."""

    def __init__(
        self,
        project_root: Path | str = ".",
        tools: Iterable[MCPTool] | None = None,
        server_name: str = SERVER_NAME,
        version: str = __version__,
    ) -> None:
        self.project_root = Path(project_root).resolve()
        self.tools: dict[str, MCPTool] = {
            tool.name: tool for tool in (tools if tools is not None else build_mcp_tools())
        }
        self.server_name = server_name
        self.version = version
        self.client_info: dict[str, Any] = {}

    # -- protocol ----------------------------------------------------------
    def handle_message(self, message: dict[str, Any]) -> dict[str, Any] | None:
        """Handle one JSON-RPC message; returns a response or ``None`` for notifications."""
        request_id = message.get("id")
        method = message.get("method")
        params = message.get("params") or {}

        if request_id is None:
            # Notification (e.g. notifications/initialized): no response is sent.
            return None
        if not isinstance(method, str):
            return self._error(request_id, INVALID_PARAMS, "Missing 'method'.")

        try:
            result = self._dispatch(method, params)
        except MCPError as exc:
            return self._error(request_id, exc.code, str(exc))
        except Exception as exc:  # pragma: no cover - defensive
            return self._error(request_id, INTERNAL_ERROR, f"Internal error: {exc}")
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    def _dispatch(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        if method == "initialize":
            self.client_info = params.get("clientInfo") or {}
            requested = params.get("protocolVersion")
            protocol = (
                requested if requested in SUPPORTED_PROTOCOL_VERSIONS else DEFAULT_PROTOCOL_VERSION
            )
            return {
                "protocolVersion": protocol,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": self.server_name, "version": self.version},
            }
        if method in {"notifications/initialized", "initialized"}:
            return {}
        if method == "ping":
            return {}
        if method == "tools/list":
            return {"tools": [self._tool_descriptor(tool) for tool in self.tools.values()]}
        if method == "tools/call":
            return self._call_tool(params)
        if method == "resources/list":
            return {"resources": []}
        if method == "prompts/list":
            return {"prompts": []}
        raise MCPError(METHOD_NOT_FOUND, f"Method not found: {method}")

    def _tool_descriptor(self, tool: MCPTool) -> dict[str, Any]:
        return {
            "name": tool.name,
            "description": tool.description,
            "inputSchema": tool.input_schema,
        }

    def _call_tool(self, params: dict[str, Any]) -> dict[str, Any]:
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if not isinstance(name, str):
            raise MCPError(INVALID_PARAMS, "'name' is required for tools/call.")
        if not isinstance(arguments, dict):
            raise MCPError(INVALID_PARAMS, "'arguments' must be an object.")

        tool = self.tools.get(name)
        if tool is None:
            raise MCPError(
                INVALID_PARAMS,
                f"Unknown tool '{name}'. Available tools: {', '.join(sorted(self.tools))}.",
            )

        try:
            text = tool.handler(arguments, self.project_root)
        except Exception as exc:
            return {
                "content": [{"type": "text", "text": f"Error: {exc}"}],
                "isError": True,
            }
        return {"content": [{"type": "text", "text": text}], "isError": False}

    @staticmethod
    def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}

    # -- transport ---------------------------------------------------------
    def serve(self, stdin: IO[str] | None = None, stdout: IO[str] | None = None) -> int:
        """Read newline-delimited JSON-RPC from stdin and write responses to stdout."""
        stream_in = stdin if stdin is not None else sys.stdin
        stream_out = stdout if stdout is not None else sys.stdout

        for line in stream_in:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                message = json.loads(stripped)
            except json.JSONDecodeError:
                response: dict[str, Any] | None = self._error(None, PARSE_ERROR, "Invalid JSON.")
            else:
                response = (
                    self.handle_message(message)
                    if isinstance(message, dict)
                    else self._error(None, INVALID_PARAMS, "Message must be a JSON object.")
                )
            if response is not None:
                stream_out.write(json.dumps(response) + "\n")
                stream_out.flush()
        return 0


__all__ = [
    "DEFAULT_PROTOCOL_VERSION",
    "SERVER_NAME",
    "SUPPORTED_PROTOCOL_VERSIONS",
    "MCPError",
    "MCPServer",
]
