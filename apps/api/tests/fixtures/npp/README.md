# NPP fixture provenance

Captured live from `https://npp.gov.in` on **2026-08-27**, via plain `curl`
with no auth, cookies, or session state:

```bash
curl -sS https://npp.gov.in/dashBoard/getBMapData
curl -sS https://npp.gov.in/dashBoard/get_generation_chart_list
curl -sS https://npp.gov.in/dashBoard/getAllZone
```

`get_generation_chart_list.json` and `get_all_zone.json` are the **full,
unmodified** real responses (4KB and 8KB — small enough to keep whole).

`get_bmap_data.json` is a **trimmed subset** of the real 758KB response —
rows were dropped, but every value that remains is verbatim from the live
payload. Nothing was invented, renamed, or "cleaned up." Selected records
deliberately cover the schema's known rough edges so tests exercise them
against real data rather than a hypothetical:

- `station_details`: 6 of 578 — includes a THERMAL station with `plf: null`
  (`PANKI TPS EXT`, id 100850 — true of *every* station in the live
  snapshot, not cherry-picked), one HYDRO (`ALLAIN DUHANGAN HPS`), one
  NUCLEAR (`KAKRAPARA`), plus 3 more for state/org/fuel filter variety.
- `thermal_project_details`: 3 of 33 — includes `Amarkantak TPP Expansion`,
  the one thermal project with `longitude`/`latitude` both `0.0` (meaning
  *unknown*, not the actual location) and `cost_overrun: "0%"`.
- `hydro_project_details`: 3 of 34 — includes `Additional two units at
  Lower Sileru Power House`, which has `cost_over_run: "61(11.96 %)"` and
  `anticipated_commisioned_schedule_date` (note the portal's own
  misspelling of "commissioned") — the hydro array uses different field
  names than the thermal one for the same concepts, and neither array has
  a single non-null `project_id` across all 67 real records.
- `thermal_station_map_details` / `hydro_station_map_details`: 3 + 2 of
  257 + 221 — includes `ADANI POWER LIMITED KAWAI TPP`, which has
  semicolon-delimited multi-unit fields (`units: "2; 1"`,
  `unit_capacity: "660; 660"`, `cod: "24-12-2013; 28-05-2013"`).
- `stateList` / `zoneList` / `distList`: 5 / 3 / 4 of 40 / 6 / 555 — plain
  reference data, no edge cases to preserve.

If NPP's schema changes, recapture with the same `curl` commands, diff
against this file, and re-select fixture rows the same way — don't hand-edit
values to make a test pass.
