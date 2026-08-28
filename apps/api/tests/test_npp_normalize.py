"""Pure-function tests for app/portals/npp/normalize.py — no network, no
DB. The messy input strings tested here (e.g. "61(11.96 %)", "0 Y, 2 M",
the misspelled anticipated_commisioned_schedule_date key) are taken
verbatim from real NPP records — see tests/fixtures/npp/README.md.
"""

from datetime import date

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


def test_parse_float_handles_none_and_blank():
    assert parse_float(None) is None
    assert parse_float("") is None
    assert parse_float("NA") is None
    assert parse_float("-") is None


def test_parse_float_handles_numeric_strings_and_numbers():
    assert parse_float("660") == 660.0
    assert parse_float(660) == 660.0
    assert parse_float(660.5) == 660.5
    assert parse_float("garbage") is None


def test_parse_coord_zero_is_unknown_sentinel():
    # Real: Amarkantak TPP Expansion has longitude=0.0, latitude=0.0 —
    # meaning "unknown," not an actual point.
    assert parse_coord(0.0, 0.0) is None


def test_parse_coord_valid_indian_point():
    coords = parse_coord(26.4766, 80.241)  # PANKI TPS EXT, real record
    assert coords is not None
    assert coords.lat == 26.4766
    assert coords.lon == 80.241


def test_parse_coord_out_of_india_bbox_is_none():
    assert parse_coord(51.5, -0.1) is None  # London — not a real NPP point


def test_parse_coord_none_inputs():
    assert parse_coord(None, 80.241) is None
    assert parse_coord(26.4766, None) is None


def test_parse_percent_with_absolute():
    # Real: hydro_project_details "Additional two units at Lower Sileru
    # Power House" has cost_over_run="61(11.96 %)"
    overrun = parse_percent("61(11.96 %)")
    assert overrun.raw == "61(11.96 %)"
    assert overrun.pct == 11.96
    assert overrun.absolute == 61.0


def test_parse_percent_simple():
    # Real: Amarkantak TPP Expansion cost_overrun="0%"
    overrun = parse_percent("0%")
    assert overrun.raw == "0%"
    assert overrun.pct == 0.0
    assert overrun.absolute is None


def test_parse_percent_unparseable_keeps_raw():
    overrun = parse_percent("garbage")
    assert overrun.raw == "garbage"
    assert overrun.pct is None
    assert overrun.absolute is None


def test_parse_percent_none():
    overrun = parse_percent(None)
    assert overrun.raw is None
    assert overrun.pct is None


def test_parse_duration():
    # Real: "0 Y, 2 M" and "0 Y, 0 M" both appear in captured project data.
    overrun = parse_duration("0 Y, 2 M")
    assert overrun.years == 0
    assert overrun.months == 2
    assert overrun.total_months == 2

    zero = parse_duration("0 Y, 0 M")
    assert zero.total_months == 0


def test_parse_duration_unparseable_keeps_raw():
    overrun = parse_duration("some other format")
    assert overrun.raw == "some other format"
    assert overrun.total_months is None


def test_split_multi():
    # Real: ADANI POWER LIMITED KAWAI TPP has units="2; 1",
    # unit_capacity="660; 660", cod="24-12-2013; 28-05-2013"
    assert split_multi("2; 1") == ["2", "1"]
    assert split_multi("660; 660") == ["660", "660"]
    assert split_multi(None) == []
    assert split_multi("") == []
    assert split_multi("single") == ["single"]


def test_parse_dmy_numeric_format():
    # Real: cod dates use "24-12-2013"
    assert parse_dmy("24-12-2013") == date(2013, 12, 24)


def test_parse_dmy_month_name_format():
    # Real: anticipated_trial_run_date uses "01-Mar-2030"
    assert parse_dmy("01-Mar-2030") == date(2030, 3, 1)


def test_parse_dmy_unrecognized_format_returns_none():
    assert parse_dmy("2030/03/01") is None
    assert parse_dmy(None) is None
    assert parse_dmy("") is None


def test_parse_epoch_ms():
    # 1787509800000 appears as a real reporting_date in getAllZone.
    result = parse_epoch_ms(1787509800000)
    assert result is not None
    assert result.year >= 2026


def test_parse_epoch_ms_none():
    assert parse_epoch_ms(None) is None


def test_field_alias_picks_first_present():
    assert field_alias({"a": 1, "b": 2}, "a", "b") == 1
    assert field_alias({"b": 2}, "a", "b") == 2


def test_field_alias_absorbs_hydro_misspelling():
    # Real hydro record uses this exact (misspelled) key where the thermal
    # array uses anticipated_trial_run_date instead.
    rec = {"anticipated_commisioned_schedule_date": "31-10-2025"}
    assert field_alias(rec, "anticipated_trial_run_date", "anticipated_commisioned_schedule_date") == "31-10-2025"


def test_field_alias_none_when_absent():
    assert field_alias({}, "a", "b") is None


def test_stable_ref_deterministic():
    ref1 = stable_ref("Amarkantak TPP Expansion", "Madhya Pradesh", "6")
    ref2 = stable_ref("Amarkantak TPP Expansion", "Madhya Pradesh", "6")
    assert ref1 == ref2
    assert len(ref1) == 10


def test_stable_ref_differs_for_different_input():
    assert stable_ref("A", "B", "C") != stable_ref("A", "B", "D")
