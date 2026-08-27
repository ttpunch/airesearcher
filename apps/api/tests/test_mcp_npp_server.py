"""Tests for the standalone MCP server (app/mcp_servers/npp_server.py).

build_npp_mcp_server(client) takes the client as a parameter — the MCP
equivalent of this project's get_ask_runner/query_fn dependency-injection
seams — so these tests build a server around a MockTransport-backed
NppClient and never touch stdio, a subprocess, or the real network. Only
main() constructs a real client.
"""

import json
import uuid
from pathlib import Path

import httpx
import pytest
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError, UnexpectedToolError

from app.mcp_servers.npp_server import build_npp_mcp_server
from app.portals.npp.client import NppClient

FIXTURES = Path(__file__).parent / "fixtures" / "npp"
BMAP_DATA = json.loads((FIXTURES / "get_bmap_data.json").read_text())


def _handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/robots.txt":
        return httpx.Response(404)
    if request.url.path == "/dashBoard/getBMapData":
        return httpx.Response(200, json=BMAP_DATA)
    return httpx.Response(404)


def make_server() -> MCPServer:
    base_url = f"https://npp-test-{uuid.uuid4().hex}.example"
    http_client = httpx.AsyncClient(transport=httpx.MockTransport(_handler), base_url=base_url)
    client = NppClient(base_url=base_url, client=http_client)
    return build_npp_mcp_server(client)


EXPECTED_TOOL_NAMES = {
    "npp_find_power_stations",
    "npp_get_power_station",
    "npp_summarize_capacity",
    "npp_find_projects",
    "npp_get_generation_trend",
    "npp_get_capacity_snapshot",
    "npp_list_regions",
}


async def test_all_seven_npp_tools_registered():
    server = make_server()
    tools = await server.list_tools()
    assert {t.name for t in tools} == EXPECTED_TOOL_NAMES


async def test_every_tool_is_marked_read_only_with_description_and_schema():
    server = make_server()
    tools = await server.list_tools()
    for t in tools:
        assert t.annotations is not None
        assert t.annotations.read_only_hint is True
        assert t.annotations.destructive_hint is False
        assert t.description
        assert t.input_schema
        assert t.output_schema is not None  # structured_output=True on every registration


async def test_datasets_and_attribution_resources_present():
    server = make_server()
    resources = await server.list_resources()
    uris = {str(r.uri) for r in resources}
    assert "npp://attribution" in uris
    assert "npp://datasets" in uris


async def test_call_tool_returns_structured_content():
    server = make_server()
    result = await server.call_tool("npp_summarize_capacity", {"group_by": "fuel"})
    assert result.structured_content is not None
    assert result.structured_content["group_by"] == "fuel"
    assert result.structured_content["rows"]


async def test_call_tool_with_bad_station_id_is_anticipated_not_a_crash():
    # MCPServer.call_tool() itself always raises on tool failure (it's the
    # protocol-level request handler, not call_tool(), that turns a
    # ToolError into a clean CallToolResult(is_error=True) — see
    # mcp.server.mcpserver.server._handle_call_tool). What this test
    # verifies instead is the thing app/mcp_servers/npp_server.py's
    # _translate_portal_errors() is actually responsible for: the tool's
    # PortalToolError must come out as a plain ToolError (an "anticipated
    # failure" per its docstring), never as its UnexpectedToolError
    # subclass (a "crash" that gets a traceback and an opaque message).
    server = make_server()
    with pytest.raises(ToolError) as exc_info:
        await server.call_tool("npp_get_power_station", {"station_id": 999999999})
    assert not isinstance(exc_info.value, UnexpectedToolError)
    assert "npp_find_power_stations" in str(exc_info.value)
