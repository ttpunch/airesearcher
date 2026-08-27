"""NPP endpoint inventory.

Every endpoint below was fetched and inspected directly (curl, no
browser/session) on 2026-08-27 — see tests/fixtures/npp/README.md for the
exact commands and captured sizes.

A few more endpoint names are referenced from the sibling
`cp-map-dashboard` page's markup (getAllStateWithZone, getStateCpt,
get_hydro_list, get_installed_capacity_list) but were never actually
fetched this session, so no parser is written against a response shape
nobody has seen — that would be exactly the kind of fabrication this
project's sourcing discipline exists to prevent (see AGENTS.md's
GeM-crawler discussion for the same principle applied elsewhere).
`/res/getWbDbData` was checked and is dead (404).
"""

BMAP_DATA_PATH = "/dashBoard/getBMapData"
GENERATION_CHART_PATH = "/dashBoard/get_generation_chart_list"
ALL_ZONE_PATH = "/dashBoard/getAllZone"

# Cache TTLs. Station/project/capacity data changes at most daily in
# practice; the generation trend is an annual series that changes at most
# once a year. Conservative TTLs also keep this client's request volume
# low against a government site with no published rate-limit policy.
BMAP_DATA_TTL_SECONDS = 6 * 60 * 60  # 6h
ALL_ZONE_TTL_SECONDS = 6 * 60 * 60  # 6h
GENERATION_CHART_TTL_SECONDS = 24 * 60 * 60  # 24h

DASHBOARD_URL = "https://npp.gov.in/dashBoard/gc-map-dashboard"

ATTRIBUTION = (
    "Source: National Power Portal (npp.gov.in), Ministry of Power / "
    "Central Electricity Authority, Government of India."
)
