# HWR tenders fixture provenance

Captured live from `https://hwr.bhel.com/tenders/onlinetenders/tenderlist.jsp`
on **2026-08-27**, via plain `curl` with no auth, cookies, or session state:

```bash
curl -A "Mozilla/5.0" https://hwr.bhel.com/tenders/onlinetenders/tenderlist.jsp
```

`tenderlist.html` is a **trimmed** subset of the real ~282KB response (126
live rows at capture time) — 2 real rows kept verbatim, wrapped in a
minimal `<table>` so the row-splitting parser (`app/crawler/hwr_tenders.py`)
sees the same `<tr>` structure it sees in production. Nothing was
invented, renamed, or reformatted — every byte inside a kept `<tr>` is
copied from the real response, including the three HTML-comment-wrapped
columns (Estimated Quantity/Cost, Last Date for Sale, Last Date to
Submit) that a browser doesn't render but the parser still reads.

The three kept rows were chosen to cover:
- NIT-19169: a plain numeric `estimated_value` ("14") and the real
  GeM-style `tender_ref` format (`GEM/2026/B/...`)
- NIT-19168: a unit-suffixed `estimated_value` ("18163 Kg")
- NIT-19140: a real BHEL-side data-entry quirk — the Tender No column
  holds a full sentence ("BID NO- GEM/2026/B/7953132 NOTE-ALL FUTURE
  CORRIGENDUM...") instead of a bare reference, past the 128-char
  `tender_ref` column limit. `_normalize_tender_ref` in
  app/crawler/hwr_tenders.py extracts the real embedded GeM number
  rather than crashing the sync or truncating a meaningful reference —
  this row is what caught the bug (a live sync against the real site
  hit a real `StringDataRightTruncationError` before the fix existed).

Separately verified against the **full, unmodified** 126-row response
this session (not committed as a fixture — too large, and largely
redundant with the trimmed sample):
- All 126 rows parsed without falling back to the NIT-serial
  `tender_ref` default, and without a missing `closing_date` or
  `published_date`.
- One genuine real-world duplicate: NIT-19072 and NIT-19073 share the
  same `tender_ref` (`BHEL/HWR/CDX/ENQ/2627-003`) and are identical in
  every other field — an administrative duplicate on BHEL's own side,
  not a parsing bug. `sync_hwr_tenders` correctly collapses these into
  one `Tender` row when deduping by `tender_ref`, which loses nothing
  distinguishable since the two source rows carry no distinct
  information beyond an internal NIT serial this project doesn't store.

If the page's structure changes, recapture with the same `curl` command,
diff against this file, and re-select fixture rows the same way — don't
hand-edit values to make a test pass.
