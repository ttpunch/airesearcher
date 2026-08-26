from app.processing.tender_extraction import (
    ExtractedTenderFields,
    extract_tender_fields,
)

SAMPLE_TENDER_TEXT = """
Tender Notice

Tender No: BHEL/PSNR/2026/CIVIL/0042

Bharat Heavy Electricals Limited invites sealed bids for the supply and
installation of boiler auxiliary equipment at its Trichy plant.

Last date for submission: 15-Mar-2026

EMD: Rs. 2,50,000/- (Rupees Two Lakh Fifty Thousand only) shall be
submitted along with the bid.

Eligibility criteria: Bidders shall have experience of executing at least
two similar works of value not less than Rs. 1 crore each in the last
five years. Minimum turnover of Rs. 5 crore in the last three financial
years is required for pre-qualification.

Bids not meeting the above eligibility criteria will be summarily rejected.
"""


def test_extracts_tender_ref():
    result = extract_tender_fields(SAMPLE_TENDER_TEXT)
    assert result.tender_ref == "BHEL/PSNR/2026/CIVIL/0042"


def test_extracts_closing_date_text():
    result = extract_tender_fields(SAMPLE_TENDER_TEXT)
    assert result.closing_date_text == "15-Mar-2026"


def test_extracts_emd_amount():
    result = extract_tender_fields(SAMPLE_TENDER_TEXT)
    assert result.emd_amount_text == "2,50,000"


def test_extracts_eligibility_snippets():
    result = extract_tender_fields(SAMPLE_TENDER_TEXT)
    assert len(result.eligibility_snippets) >= 2
    assert any("turnover" in s.lower() for s in result.eligibility_snippets)
    assert any("experience" in s.lower() for s in result.eligibility_snippets)


def test_missing_fields_are_null_not_guessed():
    result = extract_tender_fields("This document has no tender-specific fields in it at all.")
    assert result.closing_date_text is None
    assert result.emd_amount_text is None
    assert result.tender_ref is None
    assert result.eligibility_snippets == []


def test_empty_text():
    result = extract_tender_fields("")
    assert result.closing_date_text is None
    assert result.eligibility_snippets == []


def test_round_trips_through_json():
    original = extract_tender_fields(SAMPLE_TENDER_TEXT)
    restored = ExtractedTenderFields.from_json(original.to_json())
    assert restored == original


def test_eligibility_snippet_cap():
    text = "\n".join(f"Eligibility criteria clause {i} about experience." for i in range(10))
    result = extract_tender_fields(text)
    assert len(result.eligibility_snippets) == 5
