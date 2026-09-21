"""Unit tests for the minimal MCP stdio server and its tools."""

from __future__ import annotations

import io
import json
from pathlib import Path

from agent_kit.cli.main import app
from agent_kit.mcp import MCPServer, build_mcp_tools


def _out(result) -> str:
    combined = getattr(result, "output", "") or ""
    stderr = getattr(result, "stderr", "") or ""
    if stderr and stderr not in combined:
        return f"{combined}\n{stderr}"
    return combined


def _request(server: MCPServer, method: str, params: dict | None = None, request_id: int = 1):
    return server.handle_message(
        {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}}
    )


def _call(server: MCPServer, name: str, arguments: dict):
    return _request(server, "tools/call", {"name": name, "arguments": arguments})


# --- protocol -------------------------------------------------------------
def test_initialize_returns_server_info(mock_project: Path) -> None:
    server = MCPServer(mock_project)

    response = _request(
        server,
        "initialize",
        {"protocolVersion": "2025-06-18", "clientInfo": {"name": "kiro"}},
    )

    result = response["result"]
    assert result["protocolVersion"] == "2025-06-18"
    assert result["serverInfo"]["name"] == "agent-kit"
    assert result["capabilities"]["tools"] == {"listChanged": False}
    assert server.client_info == {"name": "kiro"}


def test_initialize_falls_back_for_unknown_protocol_version(mock_project: Path) -> None:
    server = MCPServer(mock_project)
    response = _request(server, "initialize", {"protocolVersion": "1999-01-01"})
    assert response["result"]["protocolVersion"] == "2025-06-18"


def test_notifications_get_no_response(mock_project: Path) -> None:
    server = MCPServer(mock_project)
    assert server.handle_message({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None


def test_ping(mock_project: Path) -> None:
    assert _request(MCPServer(mock_project), "ping")["result"] == {}


def test_unknown_method_returns_jsonrpc_error(mock_project: Path) -> None:
    response = _request(MCPServer(mock_project), "does/not/exist")
    assert response["error"]["code"] == -32601
    assert "Method not found" in response["error"]["message"]


def test_resources_and_prompts_are_empty_but_valid(mock_project: Path) -> None:
    server = MCPServer(mock_project)
    assert _request(server, "resources/list")["result"] == {"resources": []}
    assert _request(server, "prompts/list")["result"] == {"prompts": []}


# --- tools/list -----------------------------------------------------------
def test_tools_list_exposes_the_four_agent_kit_tools(mock_project: Path) -> None:
    response = _request(MCPServer(mock_project), "tools/list")

    tools = response["result"]["tools"]
    names = {tool["name"] for tool in tools}
    assert names == {
        "agent_kit_run_workflow",
        "agent_kit_evaluate",
        "agent_kit_capabilities",
        "agent_kit_read_skill",
    }
    for tool in tools:
        assert tool["description"]
        assert tool["inputSchema"]["type"] == "object"


def test_build_mcp_tools_is_side_effect_free() -> None:
    tools = build_mcp_tools()
    assert len(tools) == 4
    assert all(callable(tool.handler) for tool in tools)


# --- tools/call -----------------------------------------------------------
def test_capabilities_reports_configuration(mock_project: Path) -> None:
    response = _call(MCPServer(mock_project), "agent_kit_capabilities", {})

    text = response["result"]["content"][0]["text"]
    assert response["result"]["isError"] is False
    assert "providers: mock, openai" in text
    assert "model: mock/mock-model" in text
    assert "requirement-analysis" in text


def test_run_workflow_returns_a_valid_summary(mock_project: Path) -> None:
    server = MCPServer(mock_project)

    response = _call(
        server,
        "agent_kit_run_workflow",
        {
            "input_text": "Build an e-commerce product management API.",
            "write_output": "output/mcp.md",
        },
    )

    result = response["result"]
    assert result["isError"] is False
    text = result["content"][0]["text"]
    assert "valid: True" in text
    assert "# Requirement Summary" in text
    assert (mock_project / "output" / "mcp.md").is_file()


def test_run_workflow_accepts_a_project_file(mock_project: Path) -> None:
    response = _call(
        MCPServer(mock_project),
        "agent_kit_run_workflow",
        {"input_file": "samples/requirement-analysis/input/sample-001.md"},
    )
    assert "valid: True" in response["result"]["content"][0]["text"]


def test_run_workflow_requires_an_input(mock_project: Path) -> None:
    response = _call(MCPServer(mock_project), "agent_kit_run_workflow", {})
    result = response["result"]
    assert result["isError"] is True
    assert "input_text" in result["content"][0]["text"]


def test_run_workflow_refuses_paths_outside_the_project(mock_project: Path) -> None:
    response = _call(
        MCPServer(mock_project), "agent_kit_run_workflow", {"input_file": "../../etc/passwd"}
    )
    result = response["result"]
    assert result["isError"] is True
    assert "outside the project root" in result["content"][0]["text"]


def test_evaluate_reports_pass_for_good_output(mock_project: Path) -> None:
    server = MCPServer(mock_project)
    _call(server, "agent_kit_run_workflow", {"input_text": "x", "write_output": "output/ok.md"})

    response = _call(server, "agent_kit_evaluate", {"output_file": "output/ok.md"})

    text = response["result"]["content"][0]["text"]
    assert "Result: PASS" in text
    assert "✓ Open Questions" in text


def test_evaluate_reports_fail_for_bad_output(mock_project: Path) -> None:
    response = _call(MCPServer(mock_project), "agent_kit_evaluate", {"text": "# Nothing here"})
    text = response["result"]["content"][0]["text"]
    assert "Result: FAIL" in text


def test_evaluate_honours_required_concepts(mock_project: Path) -> None:
    server = MCPServer(mock_project)
    _call(server, "agent_kit_run_workflow", {"input_text": "x", "write_output": "output/ok.md"})

    response = _call(
        server,
        "agent_kit_evaluate",
        {"output_file": "output/ok.md", "required_concepts": ["blockchain"]},
    )

    text = response["result"]["content"][0]["text"]
    assert "Result: FAIL" in text
    assert "Concept: blockchain" in text


def test_read_skill_returns_markdown_instructions(mock_project: Path) -> None:
    response = _call(
        MCPServer(mock_project), "agent_kit_read_skill", {"name": "requirement-analysis"}
    )
    text = response["result"]["content"][0]["text"]
    assert "# Skill: requirement-analysis" in text
    assert "Identify the business objective." in text


def test_read_skill_reports_unknown_skill(mock_project: Path) -> None:
    response = _call(MCPServer(mock_project), "agent_kit_read_skill", {"name": "nope"})
    result = response["result"]
    assert result["isError"] is True
    assert "not found" in result["content"][0]["text"]


def test_unknown_tool_returns_jsonrpc_error(mock_project: Path) -> None:
    response = _call(MCPServer(mock_project), "nope", {})
    assert response["error"]["code"] == -32602
    assert "Unknown tool" in response["error"]["message"]


def test_missing_tool_name_is_rejected(mock_project: Path) -> None:
    response = _request(MCPServer(mock_project), "tools/call", {"arguments": {}})
    assert response["error"]["code"] == -32602


# --- transport ------------------------------------------------------------
def test_serve_reads_and_writes_newline_delimited_json(mock_project: Path) -> None:
    stdin = io.StringIO(
        json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        + "\n"
        + json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        + "\n"
        + "\n"  # blank lines are ignored
    )
    stdout = io.StringIO()

    exit_code = MCPServer(mock_project).serve(stdin=stdin, stdout=stdout)

    messages = [json.loads(line) for line in stdout.getvalue().splitlines()]
    assert exit_code == 0
    assert len(messages) == 2
    assert messages[0]["result"]["serverInfo"]["name"] == "agent-kit"
    assert len(messages[1]["result"]["tools"]) == 4


def test_serve_rejects_invalid_json_without_crashing(mock_project: Path) -> None:
    valid = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"})
    stdin = io.StringIO(f"not json\n{valid}\n")
    stdout = io.StringIO()

    MCPServer(mock_project).serve(stdin=stdin, stdout=stdout)

    messages = [json.loads(line) for line in stdout.getvalue().splitlines()]
    assert messages[0]["error"]["code"] == -32700
    assert messages[1]["result"] == {}


# --- CLI ------------------------------------------------------------------
def test_cli_mcp_tools_lists_tools(runner) -> None:
    result = runner.invoke(app, ["mcp", "tools"])

    assert result.exit_code == 0, _out(result)
    assert "agent_kit_run_workflow" in _out(result)


def test_cli_mcp_call_runs_a_tool(runner, mock_project: Path) -> None:
    result = runner.invoke(
        app,
        [
            "mcp",
            "call",
            "agent_kit_capabilities",
            "--arguments",
            "{}",
            "--project",
            str(mock_project),
        ],
    )

    assert result.exit_code == 0, _out(result)
    assert "model: mock/mock-model" in _out(result)


def test_cli_mcp_call_rejects_bad_json(runner, mock_project: Path) -> None:
    result = runner.invoke(
        app,
        [
            "mcp",
            "call",
            "agent_kit_capabilities",
            "--arguments",
            "{oops",
            "--project",
            str(mock_project),
        ],
    )

    assert result.exit_code == 1
    assert "valid JSON" in _out(result)
