"""Tests for the 7 logical NPP tools (app/portals/npp/tools.py), calling
PortalTool.fn directly — no MCP transport involved, same style as
test_deep_research_tools.py calling `.handler({...})` directly.
"""

import json
import uuid
from pathlib import Path

import httpx
import pytest

from app.portals.base import PortalToolError
from app.portals.npp.client import NppClient
from app.portals.npp.tools import build_npp_tools

FIXTURES = Path(__file__).parent / "fixtures" / "npp"
BMAP_DATA = json.loads((FIXTURES / "get_bmap_data.json").read_text())
GENERATION_CHART = json.loads((FIXTURES / "get_generation_chart_list.json").read_text())
ALL_ZONE = json.loads((FIXTURES / "get_all_zone.json").read_text())


def _handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/robots.txt":
        return httpx.Response(404)
    if request.url.path == "/dashBoard/getBMapData":
        return httpx.Response(200, json=BMAP_DATA)
    if request.url.path == "/dashBoard/get_generation_chart_list":
        return httpx.Response(200, json=GENERATION_CHART)
    if request.url.path == "/dashBoard/getAllZone":
        return httpx.Response(200, json=ALL_ZONE)
    return httpx.Response(404)


@pytest.fixture
def tools() -> dict:
    base_url = f"https://npp-test-{uuid.uuid4().hex}.example"
    http_client = httpx.AsyncClient(transport=httpx.MockTransport(_handler), base_url=base_url)
    client = NppClient(base_url=base_url, client=http_client)
    return {t.name: t.fn for t in build_npp_tools(client)}


async def test_find_power_stations_filters_by_fuel(tools):
    result = await tools["npp_find_power_stations"](fuel="HYDRO")
    assert result.total_matched > 0
    assert all(s.generating_type == "HYDRO" for s in result.stations)


async def test_find_power_stations_filters_by_state(tools):
    # PANKI TPS EXT is a real fixture record in Uttar Pradesh.
    result = await tools["npp_find_power_stations"](state="Uttar Pradesh")
    assert result.total_matched >= 1
    assert all(s.state_name == "Uttar Pradesh" for s in result.stations)


async def test_find_power_stations_limit_is_clamped(monkeypatch, tools):
    from app.core.config import settings

    monkeypatch.setattr(settings, "npp_max_tool_results", 2)
    result = await tools["npp_find_power_stations"](limit=1000)
    assert result.limit_applied == 2
    assert result.returned <= 2


async def test_find_power_stations_offset_pagination(tools):
    first_page = await tools["npp_find_power_stations"](limit=1, offset=0)
    second_page = await tools["npp_find_power_stations"](limit=1, offset=1)
    assert first_page.stations[0].station_id != second_page.stations[0].station_id
    assert first_page.total_matched == second_page.total_matched


async def test_find_power_stations_no_match_returns_hint_not_error(tools):
    result = await tools["npp_find_power_stations"](state="Nonexistent State")
    assert result.total_matched == 0
    assert result.hint is not None


async def test_get_power_station_by_id(tools):
    all_stations = await tools["npp_find_power_stations"](limit=100)
    target = all_stations.stations[0]
    result = await tools["npp_get_power_station"](station_id=target.station_id)
    assert result.station_id == target.station_id


async def test_get_power_station_unknown_id_raises_actionable_error(tools):
    # PortalToolError, not a bare ValueError — see app/portals/base.py's
    # docstring for why this stays a project-level type rather than an
    # MCP-specific one; app/mcp_servers/npp_server.py is what translates
    # it for the MCP transport (see test_mcp_npp_server.py).
    with pytest.raises(PortalToolError, match="npp_find_power_stations"):
        await tools["npp_get_power_station"](station_id=999999999)


async def test_summarize_capacity_by_state_totals_match_manual_sum(tools):
    all_stations = await tools["npp_find_power_stations"](limit=1000)
    up_stations = [s for s in all_stations.stations if s.state_name == "Uttar Pradesh"]
    expected_total = sum(s.installed_capacity_mw or 0.0 for s in up_stations)

    summary = await tools["npp_summarize_capacity"](group_by="state")
    up_row = next(r for r in summary.rows if r.group == "Uttar Pradesh")
    assert up_row.total_installed_mw == pytest.approx(expected_total, rel=1e-6)
    assert up_row.station_count == len(up_stations)


async def test_summarize_capacity_plf_coverage_reflects_nulls(tools):
    # Real fixture data: every station's plf is null, so coverage must be
    # exactly 0 — never silently treated as "PLF is 0%."
    summary = await tools["npp_summarize_capacity"](group_by="fuel")
    assert all(row.plf_coverage == 0.0 for row in summary.rows)
    assert all(row.mean_plf_percent is None for row in summary.rows)


async def test_find_projects_default_status_is_under_construction(tools):
    result = await tools["npp_find_projects"]()
    assert result.total_matched > 0
    assert all(p.status == "under_construction" for p in result.projects)


async def test_find_projects_delayed_only(tools):
    result = await tools["npp_find_projects"](status="all", delayed_only=True, limit=100)
    assert all((p.time_overrun.total_months or 0) > 0 for p in result.projects)


async def test_get_generation_trend_year_filtering(tools):
    result = await tools["npp_get_generation_trend"](from_year="2020-21", to_year="2023-24")
    assert result.total_matched > 0
    assert all("2020-21" <= y.financial_year <= "2023-24" for y in result.years)


async def test_get_capacity_snapshot_fields(tools):
    snapshot = await tools["npp_get_capacity_snapshot"]()
    assert snapshot.installed_capacity_mw is not None
    assert snapshot.by_sector


async def test_list_regions_states(tools):
    result = await tools["npp_list_regions"](kind="state")
    assert result.total_matched == len(BMAP_DATA["stateList"])
