"""Fetches and parses BHEL Haridwar's live online-tenders listing
(hwr.bhel.com/tenders/onlinetenders/) — verified live this session: no
robots.txt (404 → nothing disallowed), no auth, no JS rendering needed.
It's an old-style HTML frameset; the actual table lives in a sibling JSP
(tenderlist.jsp), fetched directly here rather than the frameset page.

One real, load-bearing quirk found by reading the raw HTML rather than
the rendered page: three of the table's ten columns (Estimated
Quantity/Cost, Last Date for Sale, Last Date to Submit) are wrapped in an
HTML comment, so a browser doesn't render them — but the comment doesn't
remove the underlying markup, so a plain HTML parse still recovers them.
"Last Date to Submit" was cross-checked against the equivalent
per-tender detail page's explicit "Tender Closing Date & Time" field for
one real NIT and matched exactly, which is why it's trusted here as
`closing_date` without needing a second fetch per tender.

The attached tender PDF is genuinely login-gated — verified live: its
download servlet 302-redirects an unauthenticated request to
loginmain.jsp. So `url` below points at the public per-tender detail
page (tender_form.jsp?ten_no=<id>, itself verified to load without auth),
never the PDF, which this project has no way to fetch.

Another real data-quality quirk, found by syncing against the live site
rather than assumed: a few rows (e.g. NIT-19140) put a whole sentence —
"BID NO- GEM/2026/B/7953132 NOTE-ALL FUTURE CORRIGENDUM..." — in the
Tender No column instead of a bare reference, well past the 128-char
column limit. `_normalize_tender_ref` extracts the real embedded GeM
number in that case rather than crashing the sync or silently truncating
a meaningful reference.
"""

import re
from dataclasses import dataclass
from datetime import UTC, date, datetime

import httpx

from app.crawler.crawl import RobotsDisallowed
from app.crawler.robots import USER_AGENT, can_fetch

BASE_URL = "https://hwr.bhel.com/tenders/onlinetenders"
LIST_URL = f"{BASE_URL}/tenderlist.jsp"
SOURCE_NAME = "BHEL Haridwar — Online Tenders"


def detail_url(ten_no: int) -> str:
    return f"{BASE_URL}/tender_form.jsp?ten_no={ten_no}"


@dataclass
class HwrTender:
    ten_no: int
    nit_serial: str
    tender_ref: str
    title: str
    estimated_value: str | None
    closing_date: date | None
    published_date: date | None
    url: str


_ROW_TEN_NO = re.compile(r"ten_no=(\d+)")
_CELL = re.compile(r"<td\b[^>]*>(.*?)</td>", re.DOTALL)
_CLOSING_DATE = re.compile(r"(\d{2}/\d{2}/\d{4})")
_GEM_REF = re.compile(r"GEM/\d{4}/[A-Z]/\d+")

# Tender.tender_ref is String(128). Verified live: a handful of real rows
# (e.g. NIT-19140) put a whole "BID NO- GEM/... NOTE-ALL FUTURE
# CORRIGENDUM..." sentence in this column instead of a bare reference,
# well past 128 chars — a BHEL-side data-entry inconsistency, not a
# parsing bug. Extract the real embedded GeM number when present rather
# than either crashing on insert or silently truncating a meaningful ref.
_TENDER_REF_MAX_LEN = 128


def _normalize_tender_ref(raw: str, nit_serial: str) -> str:
    raw = raw.strip()
    if not raw:
        return nit_serial
    if len(raw) <= _TENDER_REF_MAX_LEN:
        return raw
    match = _GEM_REF.search(raw)
    if match:
        return match.group(0)
    return raw[:_TENDER_REF_MAX_LEN]


def _strip_tags(fragment: str) -> str:
    text = re.sub(r"<[^>]+>", " ", fragment)
    text = text.replace("&nbsp;", " ")
    return re.sub(r"\s+", " ", text).strip()


def _parse_ddmmyy(text: str) -> date | None:
    try:
        return datetime.strptime(text.strip(), "%d/%m/%y").replace(tzinfo=UTC).date()
    except ValueError:
        return None


def _parse_closing_date(text: str) -> date | None:
    match = _CLOSING_DATE.match(text.strip())
    if not match:
        return None
    try:
        return datetime.strptime(match.group(1), "%d/%m/%Y").replace(tzinfo=UTC).date()
    except ValueError:
        return None


def parse_tender_list(html: str) -> list[HwrTender]:
    """Cell-position parsing rather than label-text matching: this page's
    ten real data columns are consistent across every row (verified
    against all 126 live rows this session), so position is more robust
    here than hunting for label text in a decades-old hand-written JSP
    template with inconsistent internal whitespace.
    """
    tenders: list[HwrTender] = []
    for block in re.split(r"<tr\b", html)[1:]:
        block = "<tr" + block
        ten_no_match = _ROW_TEN_NO.search(block)
        if ten_no_match is None:
            continue  # header row or other non-data <tr>, not a tender

        cells = [_strip_tags(c) for c in _CELL.findall(block)]
        if len(cells) < 8:
            continue  # doesn't match the expected row shape — skip, don't guess

        nit_serial, tender_ref, description = cells[0], cells[1], cells[2]
        estimated_value = cells[3] or None
        closing_date = _parse_closing_date(cells[5])
        published_date = _parse_ddmmyy(cells[7])
        ten_no = int(ten_no_match.group(1))

        tenders.append(
            HwrTender(
                ten_no=ten_no,
                nit_serial=nit_serial,
                # Falls back to the NIT serial (a real, verifiable local
                # identifier) only when this column is blank — never a
                # fabricated placeholder. See _normalize_tender_ref for the
                # separate over-length case.
                tender_ref=_normalize_tender_ref(tender_ref, nit_serial),
                title=description or f"BHEL Haridwar tender {nit_serial}",
                estimated_value=estimated_value,
                closing_date=closing_date,
                published_date=published_date,
                url=detail_url(ten_no),
            )
        )
    return tenders


async def fetch_live_tenders(client: httpx.AsyncClient) -> list[HwrTender]:
    if not await can_fetch(client, LIST_URL):
        raise RobotsDisallowed(f"robots.txt disallows fetching {LIST_URL}")

    response = await client.get(LIST_URL, headers={"User-Agent": USER_AGENT}, timeout=30.0)
    response.raise_for_status()
    return parse_tender_list(response.text)
