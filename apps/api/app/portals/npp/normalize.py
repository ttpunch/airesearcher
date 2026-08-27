"""Pure parsing/normalization functions for NPP's messier fields. No I/O —
just str/float/None in, a small typed value out (the tiny Coordinates/
Overrun/TimeOverrun models below are plain Pydantic value objects, not
records with identity). Every function is defensive: given something it
doesn't recognize, it returns None (or an all-None result with the
original string preserved) rather than raising or guessing.

Why these exist, field by field — verified against real captured
responses (see tests/fixtures/npp/README.md), not assumed:

- Coordinates: project/station records use (0.0, 0.0) to mean "location
  unknown," not "at 0,0 in the Gulf of Guinea." Treated as a sentinel, not
  substituted or silently kept as a real coordinate.
- Cost/time overrun: e.g. "0%", "61(11.96 %)", "0 Y, 2 M" — these are
  human-readable strings, not machine numbers. "0%" is genuinely
  ambiguous (on-budget vs. not-yet-computed) and NPP publishes no data
  dictionary distinguishing the two, so the raw string is always kept
  alongside any parsed number rather than silently picking one meaning.
- Multi-unit fields: "2; 1" / "660; 660" / "24-12-2013; 28-05-2013" —
  semicolon-delimited parallel lists describing multiple generating units
  at one station. Mismatched list lengths are recorded, not guessed at.
- Field name drift between the thermal and hydro project arrays: the same
  concept is spelled differently (cost_overrun / cost_over_run,
  latest_estimated_cost_cr / latest_anticipated_cost,
  anticipated_trial_run_date / anticipated_commisioned_schedule_date —
  note the portal's own misspelling of "commissioned," preserved verbatim
  since that's the real key). field_alias() absorbs every such alias in
  one place.
"""

import hashlib
import re
from datetime import UTC, date, datetime
from typing import Any

from pydantic import BaseModel

# Generous India bounding box — enough to distinguish "a real coordinate"
# from the (0.0, 0.0) sentinel without being a precise border check.
_INDIA_LAT_RANGE = (6.0, 38.0)
_INDIA_LON_RANGE = (68.0, 98.0)

_PERCENT_WITH_ABSOLUTE = re.compile(r"^\s*(?P<absolute>-?[\d.]+)\s*\(\s*(?P<pct>-?[\d.]+)\s*%\s*\)\s*$")
_PERCENT_ONLY = re.compile(r"^\s*(?P<pct>-?[\d.]+)\s*%\s*$")
_DURATION = re.compile(r"^\s*(?P<years>-?\d+)\s*Y,\s*(?P<months>-?\d+)\s*M\s*$", re.IGNORECASE)


def parse_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text or text.upper() in {"NA", "N/A", "-"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


class Coordinates(BaseModel):
    lat: float
    lon: float


def parse_coord(lat: Any, lon: Any) -> Coordinates | None:
    lat_f, lon_f = parse_float(lat), parse_float(lon)
    if lat_f is None or lon_f is None:
        return None
    if lat_f == 0.0 and lon_f == 0.0:
        return None  # the portal's "unknown" sentinel, not a real point
    if not (_INDIA_LAT_RANGE[0] <= lat_f <= _INDIA_LAT_RANGE[1]):
        return None
    if not (_INDIA_LON_RANGE[0] <= lon_f <= _INDIA_LON_RANGE[1]):
        return None
    return Coordinates(lat=lat_f, lon=lon_f)


class Overrun(BaseModel):
    raw: str | None = None
    pct: float | None = None
    absolute: float | None = None


def parse_percent(value: Any) -> Overrun:
    if value is None:
        return Overrun(raw=None)
    text = str(value).strip()
    if not text:
        return Overrun(raw=text)

    match = _PERCENT_WITH_ABSOLUTE.match(text)
    if match:
        return Overrun(raw=text, pct=float(match.group("pct")), absolute=float(match.group("absolute")))

    match = _PERCENT_ONLY.match(text)
    if match:
        return Overrun(raw=text, pct=float(match.group("pct")))

    return Overrun(raw=text)  # unparseable — keep the original string, guess nothing


class TimeOverrun(BaseModel):
    raw: str | None = None
    years: int | None = None
    months: int | None = None
    total_months: int | None = None


def parse_duration(value: Any) -> TimeOverrun:
    if value is None:
        return TimeOverrun(raw=None)
    text = str(value).strip()
    if not text:
        return TimeOverrun(raw=text)

    match = _DURATION.match(text)
    if not match:
        return TimeOverrun(raw=text)

    years, months = int(match.group("years")), int(match.group("months"))
    return TimeOverrun(raw=text, years=years, months=months, total_months=years * 12 + months)


def split_multi(value: Any) -> list[str]:
    if value is None:
        return []
    text = str(value)
    if not text.strip():
        return []
    return [part.strip() for part in text.split(";")]


_DATE_FORMATS = ("%d-%m-%Y", "%d-%b-%Y")


def parse_dmy(value: Any) -> date | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=UTC).date()
        except ValueError:
            continue
    return None  # unrecognized format — never guess a date


def parse_epoch_ms(value: Any) -> datetime | None:
    ms = parse_float(value)
    if ms is None:
        return None
    return datetime.fromtimestamp(ms / 1000.0, tz=UTC)


def field_alias(record: dict[str, Any], *names: str) -> Any:
    """Return the first name in `names` present in `record` with a
    non-None value, else None. This is where every thermal/hydro field
    name inconsistency gets absorbed in one place — see module docstring.
    """
    for name in names:
        value = record.get(name)
        if value is not None:
            return value
    return None


def stable_ref(*parts: Any) -> str:
    """A deterministic short id for records that have no natural one (e.g.
    NPP's project_id is null on every real record captured this session).
    Built from fields likely to identify a record even if the portal later
    adds a real id — this hash is a fallback, not a permanent identity.
    """
    joined = "|".join("" if p is None else str(p) for p in parts)
    return hashlib.sha1(joined.encode("utf-8")).hexdigest()[:10]
