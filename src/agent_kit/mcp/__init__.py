"""MCP (Model Context Protocol) integration for agent-kit."""

from agent_kit.mcp.server import (
    DEFAULT_PROTOCOL_VERSION,
    SERVER_NAME,
    SUPPORTED_PROTOCOL_VERSIONS,
    MCPError,
    MCPServer,
)
from agent_kit.mcp.tools import MCPTool, MCPToolError, build_mcp_tools

__all__ = [
    "DEFAULT_PROTOCOL_VERSION",
    "SERVER_NAME",
    "SUPPORTED_PROTOCOL_VERSIONS",
    "MCPError",
    "MCPServer",
    "MCPTool",
    "MCPToolError",
    "build_mcp_tools",
]
