"""National Power Portal (npp.gov.in) integration — India's power-sector
generation/capacity data, published by the Ministry of Power / Central
Electricity Authority.

Unlike GeM (see app/core/seed.py's seed_gem_tenders docstring), NPP's
dashboard endpoints are plain, unauthenticated JSON GETs — verified live by
fetching them directly with curl, no browser session or JS execution
needed. That's what makes a real client (rather than GeM's manual-entry
workaround) possible here.

Verified live 2026-08-27, no robots.txt (404 -> nothing disallowed):

    GET /dashBoard/getBMapData               758KB: stations + projects
    GET /dashBoard/get_generation_chart_list   4KB: national generation trend
    GET /dashBoard/getAllZone                  6KB: capacity snapshot

See endpoints.py for per-endpoint detail, normalize.py for how this
project handles the payload's rough edges (inconsistent/misspelled field
names between the thermal and hydro arrays, semicolon-delimited multi-unit
strings, string-typed percentages, 0.0 as an "unknown" coordinate
sentinel), and models.py for the typed shape everything gets normalized
into.

This is the reference implementation for app/portals/'s reusable scaffold
— see docs/portals-mcp-scaffold.md for how to add a second portal.
"""
