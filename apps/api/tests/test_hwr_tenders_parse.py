"""Pure-parsing tests for app/crawler/hwr_tenders.py — no network. The
fixture is a trimmed-but-real subset of hwr.bhel.com's live tender list;
see tests/fixtures/hwr_tenders/README.md for provenance and what was
verified against the full 126-row response this session.
"""

from datetime import date
from pathlib import Path

from app.crawler.hwr_tenders import _normalize_tender_ref, detail_url, parse_tender_list

FIXTURE = (Path(__file__).parent / "fixtures" / "hwr_tenders" / "tenderlist.html").read_text(encoding="utf-8")


def test_parses_all_fixture_rows():
    tenders = parse_tender_list(FIXTURE)
    assert len(tenders) == 3
    assert {t.ten_no for t in tenders} == {19169, 19168, 19140}


def test_extracts_real_gem_ref_embedded_in_an_overlength_note():
    # Real BHEL-side data-entry quirk (NIT-19140): the Tender No column
    # holds a full sentence past the tender_ref column's 128-char limit.
    # A real live sync hit StringDataRightTruncationError on this exact
    # row before this normalization existed.
    tenders = parse_tender_list(FIXTURE)
    by_ten_no = {t.ten_no: t for t in tenders}
    assert by_ten_no[19140].tender_ref == "GEM/2026/B/7953132"
    assert len(by_ten_no[19140].tender_ref) <= 128


def test_extracts_real_gem_tender_ref():
    tenders = parse_tender_list(FIXTURE)
    by_ten_no = {t.ten_no: t for t in tenders}
    assert by_ten_no[19169].tender_ref == "GEM/2026/B/7966022"


def test_extracts_title_from_description_column():
    tenders = parse_tender_list(FIXTURE)
    by_ten_no = {t.ten_no: t for t in tenders}
    assert "SEAMLESS PIPES" in by_ten_no[19169].title


def test_extracts_commented_out_estimated_value_columns():
    # Real quirk: these columns are wrapped in an HTML comment (invisible
    # in a browser) but still present in the raw markup.
    tenders = parse_tender_list(FIXTURE)
    by_ten_no = {t.ten_no: t for t in tenders}
    assert by_ten_no[19169].estimated_value == "14"
    assert by_ten_no[19168].estimated_value == "18163 Kg"


def test_closing_date_matches_last_date_to_submit_column():
    # Cross-checked against the real per-tender detail page's explicit
    # "Tender Closing Date & Time" field for NIT-19169 this session —
    # both read 2026-09-07.
    tenders = parse_tender_list(FIXTURE)
    by_ten_no = {t.ten_no: t for t in tenders}
    assert by_ten_no[19169].closing_date == date(2026, 9, 7)
    assert by_ten_no[19168].closing_date == date(2026, 9, 8)


def test_published_date_parses_two_digit_year():
    tenders = parse_tender_list(FIXTURE)
    by_ten_no = {t.ten_no: t for t in tenders}
    assert by_ten_no[19169].published_date == date(2026, 8, 27)
    assert by_ten_no[19168].published_date == date(2026, 8, 27)
    assert by_ten_no[19140].published_date == date(2026, 8, 24)


def test_url_points_at_public_detail_page_not_gated_pdf():
    tenders = parse_tender_list(FIXTURE)
    by_ten_no = {t.ten_no: t for t in tenders}
    assert by_ten_no[19169].url == detail_url(19169)
    assert "servlet/Download" not in by_ten_no[19169].url


def test_ignores_non_data_rows():
    html = "<html><body><table><tr><td>header</td></tr></table></body></html>"
    assert parse_tender_list(html) == []


def test_skips_row_with_unexpected_cell_count_rather_than_guessing():
    html = """
    <table>
    <tr><td><a href='tender_form.jsp?ten_no=1'>NIT-1</a></td><td>only two cells</td></tr>
    </table>
    """
    assert parse_tender_list(html) == []


def test_normalize_tender_ref_truncates_when_no_gem_ref_embedded():
    # Belt-and-suspenders for an over-length ref with no extractable GeM
    # number — every real case seen this session did have one, but the
    # column-length guard must not crash regardless.
    overlong = "X" * 200
    result = _normalize_tender_ref(overlong, "NIT-1")
    assert result == overlong[:128]
    assert len(result) == 128


def test_normalize_tender_ref_falls_back_to_nit_serial_when_blank():
    assert _normalize_tender_ref("", "NIT-1") == "NIT-1"
    assert _normalize_tender_ref("   ", "NIT-1") == "NIT-1"


def test_tender_ref_falls_back_to_nit_serial_when_missing():
    html = """
    <table>
    <tr>
      <td><a href='tender_form.jsp?ten_no=42'>NIT-42</a></td>
      <td></td>
      <td>Some description</td>
      <td>1</td>
      <td>01/01/2026 1:00PM</td>
      <td>01/01/2026 1:00PM</td>
      <td>01/01/2026 1:30PM</td>
      <td>01/01/26</td>
      <td>No</td>
      <td>No Change</td>
    </tr>
    </table>
    """
    tenders = parse_tender_list(html)
    assert len(tenders) == 1
    assert tenders[0].tender_ref == "NIT-42"
