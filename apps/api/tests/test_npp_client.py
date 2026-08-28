"""NppClient tests against httpx.MockTransport — no real network, ever.
Fixtures are trimmed-but-real NPP responses; see
tests/fixtures/npp/README.md for provenance.
"""

import asyncio
import json
import uuid
from pathlib import Path

import httpx
import pytest

from app.portals.base import PortalDisallowed, PortalSchemaDrift, PortalUnavailable
from app.portals.npp.client import NppClient

FIXTURES = Path(__file__).parent / "fixtures" / "npp"
BMAP_DATA = json.loads((FIXTURES / "get_bmap_data.json").read_text())
GENERATION_CHART = json.loads((FIXTURES / "get_generation_chart_list.json").read_text())
ALL_ZONE = json.loads((FIXTURES / "get_all_zone.json").read_text())


def make_client(handler, **kwargs) -> NppClient:
    # A fresh, unique origin per client: app.crawler.robots caches parsed
    # robots.txt rules in a *module-level* dict keyed by origin, so reusing
    # one hostname across tests with different robots.txt bodies (e.g.
    # allow-all vs. disallow-all) would leak whichever test happened to
    # populate that cache entry first. The path-based fixture routing
    # below doesn't care what the hostname is, so this fully isolates
    # each test's robots.txt behavior for free.
    base_url = f"https://npp-test-{uuid.uuid4().hex}.example"
    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(transport=transport, base_url=base_url)
    kwargs.setdefault("max_retries", 1)
    return NppClient(base_url=base_url, client=http_client, **kwargs)


def default_handler(call_log: list[str] | None = None):
    def handler(request: httpx.Request) -> httpx.Response:
        if call_log is not None:
            call_log.append(request.url.path)
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        if request.url.path == "/dashBoard/getBMapData":
            return httpx.Response(200, json=BMAP_DATA)
        if request.url.path == "/dashBoard/get_generation_chart_list":
            return httpx.Response(200, json=GENERATION_CHART)
        if request.url.path == "/dashBoard/getAllZone":
            return httpx.Response(200, json=ALL_ZONE)
        return httpx.Response(404)

    return handler


async def test_stations_parses_fixture_count():
    client = make_client(default_handler())
    stations = await client.stations()
    assert len(stations) == len(BMAP_DATA["station_details"])


async def test_station_carries_provenance():
    client = make_client(default_handler())
    stations = await client.stations()
    station = stations[0]
    assert station.npp_ref.startswith("station:")
    assert station.source_endpoint.endswith("/dashBoard/getBMapData")
    assert station.retrieved_at is not None


async def test_projects_combines_all_four_datasets():
    client = make_client(default_handler())
    projects = await client.projects()
    expected = (
        len(BMAP_DATA["thermal_project_details"])
        + len(BMAP_DATA["hydro_project_details"])
        + len(BMAP_DATA["thermal_station_map_details"])
        + len(BMAP_DATA["hydro_station_map_details"])
    )
    assert len(projects) == expected
    statuses = {p.status for p in projects}
    assert statuses == {"under_construction", "commissioned"}


async def test_generation_years_parses_fixture():
    client = make_client(default_handler())
    years = await client.generation_years()
    assert len(years) == len(GENERATION_CHART["linechartforGeneration"])
    assert years[0].npp_ref.startswith("trend:")


async def test_capacity_snapshot_parses_fixture():
    client = make_client(default_handler())
    snapshot = await client.capacity_snapshot()
    assert snapshot.installed_capacity_mw == ALL_ZONE["monthlyAllIndiaGen"]["installed_capacity"]
    assert len(snapshot.by_sector) == len(ALL_ZONE["installed_Capacity_List"])


async def test_regions_states():
    client = make_client(default_handler())
    states = await client.regions("state")
    assert len(states) == len(BMAP_DATA["stateList"])
    assert states[0].kind == "state"


async def test_cache_hit_issues_no_second_request():
    call_log: list[str] = []
    client = make_client(default_handler(call_log))
    await client.stations()
    await client.stations()
    bmap_calls = [p for p in call_log if p == "/dashBoard/getBMapData"]
    assert len(bmap_calls) == 1


async def test_single_flight_dedupes_concurrent_calls():
    call_log: list[str] = []
    client = make_client(default_handler(call_log))
    await asyncio.gather(client.stations(), client.projects(), client.regions("state"))
    bmap_calls = [p for p in call_log if p == "/dashBoard/getBMapData"]
    assert len(bmap_calls) == 1


async def test_5xx_retried_then_succeeds():
    attempts = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        attempts["count"] += 1
        if attempts["count"] < 2:
            return httpx.Response(503)
        return httpx.Response(200, json=BMAP_DATA)

    client = make_client(handler, max_retries=2)
    stations = await client.stations()
    assert len(stations) == len(BMAP_DATA["station_details"])
    assert attempts["count"] == 2


async def test_5xx_exhausted_raises_portal_unavailable():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(503)

    client = make_client(handler, max_retries=1)
    with pytest.raises(PortalUnavailable):
        await client.stations()


async def test_404_not_retried():
    attempts = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        attempts["count"] += 1
        return httpx.Response(404)

    client = make_client(handler, max_retries=2)
    with pytest.raises(PortalUnavailable):
        await client.stations()
    assert attempts["count"] == 1  # 404 is not in RETRYABLE_STATUS_CODES


async def test_robots_disallowed_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /\n")
        return httpx.Response(200, json=BMAP_DATA)

    client = make_client(handler)
    with pytest.raises(PortalDisallowed):
        await client.stations()


async def test_missing_expected_field_raises_schema_drift():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(200, json={"unexpected": "shape"})

    client = make_client(handler)
    with pytest.raises(PortalSchemaDrift):
        await client.stations()


async def test_non_json_200_raises_schema_drift():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(200, text="<html>not json</html>")

    client = make_client(handler)
    with pytest.raises(PortalSchemaDrift):
        await client.stations()
