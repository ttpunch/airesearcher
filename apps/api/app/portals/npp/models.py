"""Typed NPP records and search-result envelopes.

Every record carries npp_ref / source_endpoint / retrieved_at — the
provenance triple this project's citation scheme needs for a live,
changing API (see app/agent/npp_citations.py, added when these tools are
wired into the research agents): a citation isn't just "this URL" but
"this URL, this record, as of this fetch."

Envelopes (StationSearchResult etc.) always report total_matched vs.
returned so a caller can tell the difference between "there were 3
results" and "there were 400 but I only returned 20" — the token-
efficiency requirement for tools sitting in front of a 578-row dataset.
"""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel

from app.portals.npp.normalize import Coordinates, Overrun, TimeOverrun


class NppRecord(BaseModel):
    npp_ref: str
    source_endpoint: str
    retrieved_at: datetime


class NppUnit(BaseModel):
    unit_no: str | None = None
    capacity_mw: float | None = None
    cod: date | None = None


class NppStation(NppRecord):
    station_id: int
    station_name: str
    org_short_name: str | None = None
    company_name: str | None = None
    state_name: str | None = None
    zone_name: str | None = None
    sector_name: str | None = None
    generating_type: str | None = None  # THERMAL / HYDRO / NUCLEAR / ...
    installed_capacity_mw: float | None = None
    monitored_capacity_mw: float | None = None
    # PLF (Plant Load Factor) and critical_status are self-reported by the
    # generator and were null on every record captured this session — a
    # null means "not reported," never 0.
    plf_percent: float | None = None
    plf_period_days: int | None = None
    critical_status: str | None = None
    critical_reason: str | None = None
    coordinates: Coordinates | None = None
    transport_details: str | None = None


ProjectStatus = Literal["under_construction", "commissioned"]
ExpectedDateKind = Literal["cod", "anticipated_trial_run", "anticipated_commissioning"]


class NppProject(NppRecord):
    project_name: str
    organization: str | None = None
    sector: str | None = None
    state: str | None = None
    district: str | None = None
    fuel: str | None = None
    capacity_mw: float | None = None
    station_capacity_mw: float | None = None
    status: ProjectStatus
    coordinates: Coordinates | None = None
    units: list[NppUnit] = []
    units_parsed: bool = True  # False when semicolon-delimited lists had mismatched lengths
    time_overrun: TimeOverrun
    cost_overrun: Overrun
    latest_estimated_cost_cr: float | None = None
    expected_date: date | None = None
    # Which raw field expected_date came from — a real commissioning date
    # (cod) is not the same claim as an anticipated future one, and
    # conflating them would be exactly the kind of unearned certainty this
    # project's FACT/INFERENCE labeling exists to avoid.
    expected_date_kind: ExpectedDateKind | None = None


class NppGenerationYear(NppRecord):
    financial_year: str
    hydro_gwh: float | None = None
    thermal_gwh: float | None = None
    renewable_gwh: float | None = None
    nuclear_gwh: float | None = None

    @property
    def total_gwh(self) -> float | None:
        values = [self.hydro_gwh, self.thermal_gwh, self.renewable_gwh, self.nuclear_gwh]
        if any(v is None for v in values):
            return None
        return sum(v for v in values if v is not None)


class NppSectorCapacity(BaseModel):
    sector_name: str
    installed_capacity_mw: float | None = None


class NppCapacitySnapshot(NppRecord):
    reporting_date: datetime | None = None
    installed_capacity_mw: float | None = None
    monitored_capacity_mw: float | None = None
    under_maintenance_capacity_mw: float | None = None
    online_capacity_mw: float | None = None
    shutdown_capacity_mw: float | None = None
    unscheduled_capacity_mw: float | None = None
    by_sector: list[NppSectorCapacity] = []


RegionKind = Literal["state", "zone", "district"]


class NppRegion(NppRecord):
    kind: RegionKind
    region_id: int
    name: str | None = None
    zone_id: int | None = None


class SearchEnvelope(BaseModel):
    total_matched: int
    returned: int
    offset: int
    limit_applied: int
    retrieved_at: datetime
    source_endpoint: str
    source_url: str
    attribution: str
    hint: str | None = None


class StationSearchResult(SearchEnvelope):
    stations: list[NppStation]


class ProjectSearchResult(SearchEnvelope):
    projects: list[NppProject]


class GenerationTrend(SearchEnvelope):
    years: list[NppGenerationYear]


class RegionList(SearchEnvelope):
    regions: list[NppRegion]


class CapacitySummaryRow(BaseModel):
    group: str
    station_count: int
    total_installed_mw: float
    total_monitored_mw: float
    mean_plf_percent: float | None
    plf_coverage: float  # fraction of stations in this group with a non-null PLF


class CapacitySummary(SearchEnvelope):
    group_by: str
    rows: list[CapacitySummaryRow]
