"""The 7 logical NPP tools, transport-agnostic (app/portals/base.PortalTool).

build_npp_tools(client) closes each tool over one shared NppClient, the
same factory-closure convention app/agent/deep_research_tools.py already
uses for its search tools — so app/mcp_servers/npp_server.py (a standalone
MCP server) and, later, an in-process SdkMcpTool adapter can both wrap
these same function bodies.

Every list-returning tool reports total_matched vs. returned and clamps
`limit` to settings.npp_max_tool_results — none of them may dump all 578
stations into a model's context by default. A tool that matches nothing is
not an error: it returns an empty list plus a `hint` suggesting how to fix
the query (e.g. via npp_list_regions for exact state-name spelling).
"""

from typing import Literal

from app.core.config import settings
from app.portals.base import PortalTool, PortalToolError, now_utc
from app.portals.npp.client import NppClient
from app.portals.npp.endpoints import ATTRIBUTION, DASHBOARD_URL
from app.portals.npp.models import (
    CapacitySummary,
    CapacitySummaryRow,
    GenerationTrend,
    NppCapacitySnapshot,
    NppStation,
    ProjectSearchResult,
    RegionList,
    StationSearchResult,
)

GroupBy = Literal["state", "zone", "fuel", "organization", "sector"]
ProjectStatusFilter = Literal["under_construction", "commissioned", "all"]
RegionKindFilter = Literal["state", "zone", "district"]


def _clamp_limit(limit: int) -> int:
    return min(max(limit, 1), settings.npp_max_tool_results)


def _no_match_hint(**filters: str | None) -> str:
    applied = {name: value for name, value in filters.items() if value}
    if not applied:
        return "No records matched. Try broadening or removing filters."
    described = ", ".join(f"{name}={value!r}" for name, value in applied.items())
    return (
        f"No records matched {described}. Names must match NPP's exact spelling/case — use "
        "npp_list_regions to check state names, or broaden the filter."
    )


def build_npp_tools(client: NppClient) -> list[PortalTool]:
    async def npp_find_power_stations(
        state: str | None = None,
        zone: str | None = None,
        fuel: str | None = None,
        organization: str | None = None,
        name_contains: str | None = None,
        min_capacity_mw: float | None = None,
        max_capacity_mw: float | None = None,
        critical_only: bool = False,
        limit: int = 20,
        offset: int = 0,
    ) -> StationSearchResult:
        stations = await client.stations()

        def matches(s: NppStation) -> bool:
            if state and (s.state_name or "").casefold() != state.casefold():
                return False
            if zone and (s.zone_name or "").casefold() != zone.casefold():
                return False
            if fuel and (s.generating_type or "").casefold() != fuel.casefold():
                return False
            if organization and organization.casefold() not in (s.org_short_name or "").casefold():
                return False
            if name_contains and name_contains.casefold() not in s.station_name.casefold():
                return False
            if min_capacity_mw is not None and (s.installed_capacity_mw or 0.0) < min_capacity_mw:
                return False
            if max_capacity_mw is not None and (s.installed_capacity_mw or 0.0) > max_capacity_mw:
                return False
            return not (critical_only and not s.critical_status)

        filtered = [s for s in stations if matches(s)]
        filtered.sort(key=lambda s: s.installed_capacity_mw or 0.0, reverse=True)
        effective_limit = _clamp_limit(limit)
        page = filtered[offset : offset + effective_limit]

        return StationSearchResult(
            stations=page,
            total_matched=len(filtered),
            returned=len(page),
            offset=offset,
            limit_applied=effective_limit,
            retrieved_at=stations[0].retrieved_at if stations else now_utc(),
            source_endpoint=stations[0].source_endpoint if stations else "",
            source_url=DASHBOARD_URL,
            attribution=ATTRIBUTION,
            hint=None
            if filtered
            else _no_match_hint(state=state, zone=zone, fuel=fuel, organization=organization),
        )

    async def npp_get_power_station(station_id: int) -> NppStation:
        stations = await client.stations()
        for station in stations:
            if station.station_id == station_id:
                return station
        raise PortalToolError(
            f"No NPP station with station_id={station_id}. Use npp_find_power_stations to discover "
            "valid station ids first."
        )

    async def npp_summarize_capacity(
        group_by: GroupBy = "state",
        fuel: str | None = None,
        state: str | None = None,
    ) -> CapacitySummary:
        stations = await client.stations()

        def group_key(s: NppStation) -> str:
            value = {
                "state": s.state_name,
                "zone": s.zone_name,
                "fuel": s.generating_type,
                "organization": s.org_short_name,
                "sector": s.sector_name,
            }[group_by]
            return value or "Unknown"

        filtered = stations
        if fuel:
            filtered = [s for s in filtered if (s.generating_type or "").casefold() == fuel.casefold()]
        if state:
            filtered = [s for s in filtered if (s.state_name or "").casefold() == state.casefold()]

        groups: dict[str, list[NppStation]] = {}
        for station in filtered:
            groups.setdefault(group_key(station), []).append(station)

        rows: list[CapacitySummaryRow] = []
        for name, group in groups.items():
            installed = sum(s.installed_capacity_mw or 0.0 for s in group)
            monitored = sum(s.monitored_capacity_mw or 0.0 for s in group)
            plfs = [s.plf_percent for s in group if s.plf_percent is not None]
            mean_plf = sum(plfs) / len(plfs) if plfs else None
            rows.append(
                CapacitySummaryRow(
                    group=name,
                    station_count=len(group),
                    total_installed_mw=round(installed, 2),
                    total_monitored_mw=round(monitored, 2),
                    mean_plf_percent=round(mean_plf, 2) if mean_plf is not None else None,
                    # A mandatory coverage figure, not just a mean, so the model
                    # can't over-claim from PLF that's mostly unreported — see
                    # app/portals/npp/models.py's CapacitySummaryRow docstring.
                    plf_coverage=round(len(plfs) / len(group), 4) if group else 0.0,
                )
            )
        rows.sort(key=lambda r: r.total_installed_mw, reverse=True)

        return CapacitySummary(
            group_by=group_by,
            rows=rows,
            total_matched=len(filtered),
            returned=len(rows),
            offset=0,
            limit_applied=len(rows),
            retrieved_at=stations[0].retrieved_at if stations else now_utc(),
            source_endpoint=stations[0].source_endpoint if stations else "",
            source_url=DASHBOARD_URL,
            attribution=ATTRIBUTION,
            hint=None if rows else _no_match_hint(fuel=fuel, state=state),
        )

    async def npp_find_projects(
        status: ProjectStatusFilter = "under_construction",
        state: str | None = None,
        fuel: str | None = None,
        organization: str | None = None,
        min_capacity_mw: float | None = None,
        delayed_only: bool = False,
        limit: int = 20,
        offset: int = 0,
    ) -> ProjectSearchResult:
        projects = await client.projects()

        def matches(p) -> bool:
            if status != "all" and p.status != status:
                return False
            if state and (p.state or "").casefold() != state.casefold():
                return False
            if fuel and (p.fuel or "").casefold() != fuel.casefold():
                return False
            if organization and organization.casefold() not in (p.organization or "").casefold():
                return False
            if min_capacity_mw is not None and (p.capacity_mw or 0.0) < min_capacity_mw:
                return False
            return not (delayed_only and (p.time_overrun.total_months or 0) <= 0)

        filtered = [p for p in projects if matches(p)]
        filtered.sort(key=lambda p: p.capacity_mw or 0.0, reverse=True)
        effective_limit = _clamp_limit(limit)
        page = filtered[offset : offset + effective_limit]

        return ProjectSearchResult(
            projects=page,
            total_matched=len(filtered),
            returned=len(page),
            offset=offset,
            limit_applied=effective_limit,
            retrieved_at=projects[0].retrieved_at if projects else now_utc(),
            source_endpoint=projects[0].source_endpoint if projects else "",
            source_url=DASHBOARD_URL,
            attribution=ATTRIBUTION,
            hint=None
            if filtered
            else _no_match_hint(status=status, state=state, fuel=fuel, organization=organization),
        )

    async def npp_get_generation_trend(
        from_year: str | None = None,
        to_year: str | None = None,
    ) -> GenerationTrend:
        years = await client.generation_years()
        filtered = years
        if from_year:
            filtered = [y for y in filtered if y.financial_year >= from_year]
        if to_year:
            filtered = [y for y in filtered if y.financial_year <= to_year]

        return GenerationTrend(
            years=filtered,
            total_matched=len(filtered),
            returned=len(filtered),
            offset=0,
            limit_applied=len(filtered),
            retrieved_at=years[0].retrieved_at if years else now_utc(),
            source_endpoint=years[0].source_endpoint if years else "",
            source_url=DASHBOARD_URL,
            attribution=ATTRIBUTION,
            hint=None if filtered else "No financial years matched the given range.",
        )

    async def npp_get_capacity_snapshot() -> NppCapacitySnapshot:
        return await client.capacity_snapshot()

    async def npp_list_regions(
        kind: RegionKindFilter = "state",
        name_contains: str | None = None,
        limit: int = 100,
    ) -> RegionList:
        regions = await client.regions(kind)
        filtered = regions
        if name_contains:
            filtered = [r for r in filtered if name_contains.casefold() in (r.name or "").casefold()]
        effective_limit = _clamp_limit(limit)
        page = filtered[:effective_limit]

        return RegionList(
            regions=page,
            total_matched=len(filtered),
            returned=len(page),
            offset=0,
            limit_applied=effective_limit,
            retrieved_at=regions[0].retrieved_at if regions else now_utc(),
            source_endpoint=regions[0].source_endpoint if regions else "",
            source_url=DASHBOARD_URL,
            attribution=ATTRIBUTION,
            hint=None if filtered else _no_match_hint(name_contains=name_contains),
        )

    return [
        PortalTool(
            name="npp_find_power_stations",
            description=(
                "Find operating Indian power stations by state, zone, fuel type (THERMAL/HYDRO/NUCLEAR), "
                "operating organization, name substring, and/or installed-capacity range. Returns "
                "paginated results sorted by installed capacity, descending. Source: National Power "
                "Portal (npp.gov.in)."
            ),
            fn=npp_find_power_stations,
        ),
        PortalTool(
            name="npp_get_power_station",
            description="Get one NPP power station's full detail by its station_id (from npp_find_power_stations).",
            fn=npp_get_power_station,
        ),
        PortalTool(
            name="npp_summarize_capacity",
            description=(
                "Aggregate installed/monitored capacity and mean Plant Load Factor (PLF) across all NPP "
                "stations, grouped by state, zone, fuel, organization, or sector. Every row reports "
                "plf_coverage (fraction of stations in that group with a reported PLF) since PLF is "
                "self-reported and often missing — a mean without its coverage would overstate confidence."
            ),
            fn=npp_summarize_capacity,
        ),
        PortalTool(
            name="npp_find_projects",
            description=(
                "Find Indian thermal/hydro power projects by status (under_construction, commissioned, "
                "or all), state, fuel, organization, minimum capacity, or whether they're running behind "
                "schedule (delayed_only). Under-construction projects carry cost/time overrun and an "
                "anticipated commissioning date; commissioned ones carry an actual COD."
            ),
            fn=npp_find_projects,
        ),
        PortalTool(
            name="npp_get_generation_trend",
            description=(
                "India's national electricity generation by fuel type (hydro/thermal/renewable/nuclear, "
                "in GWh) for each financial year from 1946-47 to the present, optionally bounded by "
                "from_year/to_year (e.g. '2010-11')."
            ),
            fn=npp_get_generation_trend,
        ),
        PortalTool(
            name="npp_get_capacity_snapshot",
            description=(
                "India's current all-India installed/monitored/online/shutdown generation capacity (MW), "
                "plus a breakdown by sector (central/state/private)."
            ),
            fn=npp_get_capacity_snapshot,
        ),
        PortalTool(
            name="npp_list_regions",
            description=(
                "List NPP's states, zones, or districts by exact name and id — use this to find the "
                "exact spelling NPP expects before filtering npp_find_power_stations/npp_find_projects "
                "by state or zone."
            ),
            fn=npp_list_regions,
        ),
    ]
