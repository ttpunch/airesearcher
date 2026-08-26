import pymupdf
import pytest

from app.processing.pdf import PdfExtractionError, extract_text


def _make_pdf(text: str) -> bytes:
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


async def test_extract_text_from_real_pdf():
    pdf_bytes = _make_pdf("BHEL Annual Report — Test Extraction")
    text = await extract_text(pdf_bytes)
    assert "BHEL Annual Report" in text
    assert "Test Extraction" in text


async def test_extract_text_multi_page():
    doc = pymupdf.open()
    doc.new_page().insert_text((72, 72), "Page one content")
    doc.new_page().insert_text((72, 72), "Page two content")
    pdf_bytes = doc.tobytes()
    doc.close()

    text = await extract_text(pdf_bytes)
    assert "Page one content" in text
    assert "Page two content" in text


async def test_extract_text_raises_on_garbage_input():
    with pytest.raises(PdfExtractionError):
        await extract_text(b"this is not a pdf")
