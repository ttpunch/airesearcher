"""Standalone MCP server entry points — separate processes speaking the
real MCP protocol over stdio (or HTTP), connectable from Claude Desktop,
Claude Code, or any other MCP client. Distinct from app.agent's in-process
claude_agent_sdk tools, which never leave this project's own FastAPI
process — see app/portals/__init__.py for how the two relate.
"""
