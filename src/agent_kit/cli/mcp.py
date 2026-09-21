"""``agent-kit mcp`` — expose the runtime to MCP clients (Kiro, other IDEs)."""

from __future__ import annotations

from pathlib import Path

import typer

from agent_kit.cli.common import info

mcp_app = typer.Typer(
    help="Model Context Protocol integration (stdio server).",
    no_args_is_help=True,
)


@mcp_app.command("serve")
def serve_command(
    project: Path = typer.Option(
        Path("."), "--project", "-p", help="Project root the MCP tools operate on."
    ),
) -> None:
    """Serve agent-kit over MCP on stdin/stdout.

    stdout carries JSON-RPC frames only; diagnostics are written to stderr.
    """
    from agent_kit.mcp.server import MCPServer

    server = MCPServer(Path(project).resolve())
    tool_names = ", ".join(sorted(server.tools))
    # stderr keeps the stdio protocol channel clean.
    typer.echo(
        f"{server.server_name} MCP server ready — project={server.project_root} tools={tool_names}",
        err=True,
    )
    raise typer.Exit(code=server.serve())


@mcp_app.command("tools")
def tools_command() -> None:
    """List the MCP tools this server exposes."""
    from agent_kit.mcp.tools import build_mcp_tools

    for tool in build_mcp_tools():
        info(f"{tool.name}\n    {tool.description}")


@mcp_app.command("call")
def call_command(
    name: str = typer.Argument(..., help="MCP tool name, e.g. agent_kit_capabilities."),
    arguments: str = typer.Option(
        "{}", "--arguments", "-a", help="JSON object with the tool arguments."
    ),
    project: Path = typer.Option(Path("."), "--project", "-p", help="Project root."),
) -> None:
    """Invoke one MCP tool locally (debugging helper)."""
    import json

    from agent_kit.mcp.server import MCPServer

    try:
        payload = json.loads(arguments)
    except json.JSONDecodeError as exc:
        info(f"✗ --arguments must be valid JSON: {exc}")
        raise typer.Exit(code=1) from exc

    server = MCPServer(Path(project).resolve())
    response = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": name, "arguments": payload},
        }
    )
    if response is None:  # pragma: no cover - defensive
        raise typer.Exit(code=1)
    if "error" in response:
        info(f"✗ {response['error']['message']}")
        raise typer.Exit(code=1)
    result = response["result"]
    for block in result.get("content", []):
        info(block.get("text", ""))
    raise typer.Exit(code=1 if result.get("isError") else 0)
