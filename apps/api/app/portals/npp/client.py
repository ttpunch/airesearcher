"""NppClient — fetches and parses the three verified NPP endpoints into the
typed models in app/portals/npp/models.py.

get_npp_client() is a process-level singleton, deliberately — a
per-request client would refetch getBMapData's ~758KB payload on every
single tool call instead of sharing the cache (see app/portals/cache.py).
Tests never touch this singleton; they construct NppClient(client=...)
directly with an httpx.MockTransport-backed client, the same pattern
VoyageEmbeddingProvider uses.
"""

from typing import Any

from app.core.config import settings
from app.portals.base import Fetched, PortalClient, PortalSchemaDrift
from app.portals.npp.endpoints import (
    ALL_ZONE_PATH,
    ALL_ZONE_TTL_SECONDS,
    BMAP_DATA_PATH,
    BMAP_DATA_TTL_SECONDS,
    GENERATION_CHART_PATH,
    GENERATION_CHART_TTL_SECONDS,
)
from app.portals.npp.models import (
    NppCapacitySnapshot,
    NppGenerationYear,
    NppProject,
    NppRegion,
    NppSectorCapacity,
    NppStation,
    NppUnit,
    RegionKind,
)
from app.portals.npp.normalize import (
    field_alias,
    parse_coord,
    parse_dmy,
    parse_duration,
    parse_epoch_ms,
    parse_float,
    parse_percent,
    split_multi,
    stable_ref,
)

# (dataset key in getBMapData) -> whether records from it are under
# construction or already commissioned. Verified against real payloads:
# thermal/hydro_project_details hold not-yet-operating projects;
# thermal/hydro_station_map_details hold already-commissioned ones (they
# carry real `cod` values, project_details don't).
_PROJECT_DATASETS = (
    ("thermal_project_details", "under_construction"),
    ("hydro_project_details", "under_construction"),
    ("thermal_station_map_details", "commissioned"),
    ("hydro_station_map_details", "commissioned"),
)

_REGION_DATASET_KEYS: dict[RegionKind, str] = {
    "state": "stateList",
    "zone": "zoneList",
    "district": "distList",
}


def _build_units(rec: dict[str, Any]) -> tuple[list[NppUnit], bool]:
    units_raw, caps_raw, cods_raw = rec.get("units"), rec.get("unit_capacity"), rec.get("cod")
    if units_raw or caps_raw or cods_raw:
        u_list, c_list, d_list = split_multi(units_raw), split_multi(caps_raw), split_multi(cods_raw)
        nonempty_lengths = {len(lst) for lst in (u_list, c_list, d_list) if lst}
        parsed_ok = len(nonempty_lengths) <= 1
        n = max((len(u_list), len(c_list), len(d_list)), default=0)
        units = [
            NppUnit(
                unit_no=u_list[i] if i < len(u_list) else None,
                capacity_mw=parse_float(c_list[i]) if i < len(c_list) else None,
                cod=parse_dmy(d_list[i]) if i < len(d_list) else None,
            )
            for i in range(n)
        ]
        return units, parsed_ok

    unit_no = rec.get("unit_no")
    if unit_no:
        return [NppUnit(unit_no=str(unit_no), capacity_mw=parse_float(rec.get("capacity")))], True
    return [], True


def _determine_expected_date(rec: dict[str, Any], units: list[NppUnit]) -> tuple[Any, str | None]:
    trial = rec.get("anticipated_trial_run_date")
    if trial:
        parsed = parse_dmy(trial)
        if parsed:
            return parsed, "anticipated_trial_run"

    anticipated_commissioning = rec.get("anticipated_commisioned_schedule_date")  # sic — real NPP field name
    if anticipated_commissioning:
        parsed = parse_dmy(anticipated_commissioning)
        if parsed:
            return parsed, "anticipated_commissioning"

    unit_cods = [u.cod for u in units if u.cod is not None]
    if unit_cods:
        return min(unit_cods), "cod"

    return None, None


def _project_ref(rec: dict[str, Any]) -> str:
    project_id = rec.get("project_id")
    if project_id is not None:
        return f"project:{project_id}"
    # Real captured data: project_id is null on every thermal and hydro
    # project record (67/67) — this hash path is the common case, not a
    # rare fallback. See normalize.stable_ref's docstring.
    name = field_alias(rec, "project_name", "station_name") or ""
    return f"project:{stable_ref(name, rec.get('state_name'), rec.get('unit_no'))}"


def parse_station(rec: dict[str, Any], source_endpoint: str, retrieved_at: Any) -> NppStation:
    station_id = rec["station_id"]
    plf_days = parse_float(rec.get("in_days"))
    return NppStation(
        npp_ref=f"station:{station_id}",
        source_endpoint=source_endpoint,
        retrieved_at=retrieved_at,
        station_id=station_id,
        station_name=rec.get("station_name") or f"Station {station_id}",
        org_short_name=rec.get("org_short_name"),
        company_name=rec.get("company_name"),
        state_name=rec.get("state_name"),
        zone_name=rec.get("zone_name"),
        sector_name=rec.get("sector_name"),
        generating_type=rec.get("generating_type_name"),
        installed_capacity_mw=parse_float(rec.get("unit_installed_capacity")),
        monitored_capacity_mw=parse_float(rec.get("unit_monitered_capacity")),
        plf_percent=parse_float(rec.get("plf")),
        plf_period_days=int(plf_days) if plf_days is not None else None,
        critical_status=rec.get("critical_status"),
        critical_reason=rec.get("reason_name"),
        coordinates=parse_coord(rec.get("latitude"), rec.get("longitude")),
        transport_details=rec.get("transport_details"),
    )


def parse_project(
    rec: dict[str, Any], status: str, source_endpoint: str, retrieved_at: Any
) -> NppProject:
    units, units_parsed = _build_units(rec)
    expected_date, expected_date_kind = _determine_expected_date(rec, units)
    return NppProject(
        npp_ref=_project_ref(rec),
        source_endpoint=source_endpoint,
        retrieved_at=retrieved_at,
        project_name=field_alias(rec, "project_name", "station_name") or "Unnamed project",
        organization=field_alias(rec, "organization_name", "organization"),
        sector=rec.get("sector_name"),
        state=rec.get("state_name"),
        district=rec.get("district_name"),
        fuel=rec.get("fuel_used_name"),
        capacity_mw=parse_float(rec.get("capacity")),
        station_capacity_mw=parse_float(rec.get("station_capacity")),
        status=status,
        coordinates=parse_coord(rec.get("latitude"), rec.get("longitude")),
        units=units,
        units_parsed=units_parsed,
        time_overrun=parse_duration(rec.get("time_overrun")),
        cost_overrun=parse_percent(field_alias(rec, "cost_overrun", "cost_over_run")),
        latest_estimated_cost_cr=parse_float(field_alias(rec, "latest_estimated_cost_cr", "latest_anticipated_cost")),
        expected_date=expected_date,
        expected_date_kind=expected_date_kind,
    )


def parse_generation_year(rec: dict[str, Any], source_endpoint: str, retrieved_at: Any) -> NppGenerationYear:
    return NppGenerationYear(
        npp_ref=f"trend:{rec['financial_year']}",
        source_endpoint=source_endpoint,
        retrieved_at=retrieved_at,
        financial_year=rec["financial_year"],
        hydro_gwh=parse_float(rec.get("hydro")),
        thermal_gwh=parse_float(rec.get("thermal_total")),
        renewable_gwh=parse_float(rec.get("renewable_energy_sources")),
        nuclear_gwh=parse_float(rec.get("nuclear")),
    )


def parse_capacity_snapshot(payload: dict[str, Any], source_endpoint: str, retrieved_at: Any) -> NppCapacitySnapshot:
    monthly = payload.get("monthlyAllIndiaGen") or {}
    by_sector = [
        NppSectorCapacity(
            sector_name=row.get("sector_name") or "Unknown",
            installed_capacity_mw=parse_float(row.get("installed_capacity")),
        )
        for row in (payload.get("installed_Capacity_List") or [])
    ]
    reporting_date = parse_epoch_ms(monthly.get("reporting_date"))
    ref_date = reporting_date.date().isoformat() if reporting_date else "unknown"
    return NppCapacitySnapshot(
        npp_ref=f"capacity:{ref_date}",
        source_endpoint=source_endpoint,
        retrieved_at=retrieved_at,
        reporting_date=reporting_date,
        installed_capacity_mw=parse_float(monthly.get("installed_capacity")),
        monitored_capacity_mw=parse_float(monthly.get("monitored_capacity")),
        under_maintenance_capacity_mw=parse_float(monthly.get("under_maintenance_capacity")),
        online_capacity_mw=parse_float(monthly.get("online_capacity")),
        shutdown_capacity_mw=parse_float(monthly.get("shutdown_capacity")),
        unscheduled_capacity_mw=parse_float(monthly.get("unscheduled_capacity")),
        by_sector=by_sector,
    )


def parse_region(rec: dict[str, Any], kind: RegionKind, source_endpoint: str, retrieved_at: Any) -> NppRegion:
    id_field = {"state": "state_id", "zone": "zone_id", "district": "district_id"}[kind]
    name_field = {"state": "state_name", "zone": "zone_name", "district": "district_name"}[kind]
    region_id = rec[id_field]
    return NppRegion(
        npp_ref=f"region:{kind}:{region_id}",
        source_endpoint=source_endpoint,
        retrieved_at=retrieved_at,
        kind=kind,
        region_id=region_id,
        name=rec.get(name_field),
        zone_id=rec.get("zone_id"),
    )


class NppClient(PortalClient):
    def __init__(
        self,
        *,
        base_url: str | None = None,
        client: Any = None,
        timeout_seconds: float | None = None,
        max_retries: int | None = None,
        cache: Any = None,
    ) -> None:
        super().__init__(
            base_url or settings.npp_base_url,
            client=client,
            timeout_seconds=timeout_seconds if timeout_seconds is not None else settings.npp_timeout_seconds,
            max_retries=max_retries if max_retries is not None else settings.npp_max_retries,
            cache=cache,
        )

    async def bmap(self) -> Fetched:
        """Public (not just an internal helper) so callers that need
        fetch-level provenance (retrieved_at/url) for an envelope — e.g.
        app/portals/npp/tools.py — can get it without re-deriving it from
        a parsed record list. The TTL cache makes this free to call
        alongside stations()/projects()/regions() in the same tool call.
        """
        return await self.get_json(BMAP_DATA_PATH, ttl_seconds=BMAP_DATA_TTL_SECONDS)

    async def generation_chart(self) -> Fetched:
        return await self.get_json(GENERATION_CHART_PATH, ttl_seconds=GENERATION_CHART_TTL_SECONDS)

    async def all_zone(self) -> Fetched:
        return await self.get_json(ALL_ZONE_PATH, ttl_seconds=ALL_ZONE_TTL_SECONDS)

    async def stations(self) -> list[NppStation]:
        fetched = await self.bmap()
        rows = fetched.payload.get("station_details")
        if rows is None:
            raise PortalSchemaDrift(
                f"{fetched.url} response no longer has a 'station_details' array — NPP may have changed "
                "its schema. Inspect the raw response before relying on this tool."
            )
        return [parse_station(row, fetched.url, fetched.retrieved_at) for row in rows]

    async def projects(self) -> list[NppProject]:
        fetched = await self.bmap()
        results: list[NppProject] = []
        for key, status in _PROJECT_DATASETS:
            rows = fetched.payload.get(key)
            if rows is None:
                continue  # one array missing this fetch isn't fatal on its own
            results.extend(parse_project(row, status, fetched.url, fetched.retrieved_at) for row in rows)
        if not results and not any(fetched.payload.get(key) is not None for key, _ in _PROJECT_DATASETS):
            raise PortalSchemaDrift(
                f"{fetched.url} response has none of the expected project/station-map arrays — NPP may "
                "have changed its schema. Inspect the raw response before relying on this tool."
            )
        return results

    async def generation_years(self) -> list[NppGenerationYear]:
        fetched = await self.generation_chart()
        rows = fetched.payload.get("linechartforGeneration")
        if rows is None:
            raise PortalSchemaDrift(
                f"{fetched.url} response no longer has 'linechartforGeneration' — NPP may have changed "
                "its schema."
            )
        return [parse_generation_year(row, fetched.url, fetched.retrieved_at) for row in rows]

    async def capacity_snapshot(self) -> NppCapacitySnapshot:
        fetched = await self.all_zone()
        return parse_capacity_snapshot(fetched.payload, fetched.url, fetched.retrieved_at)

    async def regions(self, kind: RegionKind) -> list[NppRegion]:
        fetched = await self.bmap()
        dataset_key = _REGION_DATASET_KEYS[kind]
        rows = fetched.payload.get(dataset_key)
        if rows is None:
            raise PortalSchemaDrift(
                f"{fetched.url} response no longer has '{dataset_key}' — NPP may have changed its schema."
            )
        return [parse_region(row, kind, fetched.url, fetched.retrieved_at) for row in rows]


_client: NppClient | None = None


def get_npp_client() -> NppClient:
    """Process-level singleton — see module docstring for why."""
    global _client
    if _client is None:
        _client = NppClient()
    return _client
