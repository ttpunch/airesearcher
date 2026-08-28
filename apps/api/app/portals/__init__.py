"""Reusable scaffold for wrapping external (typically government) data
portals as tool sources — for both a standalone MCP server
(app/mcp_servers/) and, later, in-process agent tools alongside
app/agent/tools.py and app/agent/deep_research_tools.py.

Nothing under app/portals/ may import from app.core.db, app.models,
app.routers, or app.main. That boundary is deliberate: it's what would let
this package become a standalone workspace member later (see
docs/portals-mcp-scaffold.md) without a rewrite, if a real second consumer
ever needs it without FastAPI/SQLAlchemy as transitive dependencies.

app/portals/npp/ is the first concrete portal built on this scaffold — see
that package's docstring for what it wraps and why. Adding a second portal
means: subclass PortalClient, write its own normalize/models modules, and
declare a list[PortalTool] — no changes needed here.
"""
