"""PDF text extraction via PyMuPDF.

No OCR fallback yet — a text-native PDF (the common case for BHEL/
government releases per Phase 1's research) extracts cleanly; a scanned
PDF currently comes back as empty text and the caller should flag it
rather than silently accepting empty content. OCR is a deliberate
follow-up, not an oversight — added once a real scanned document shows
up in practice, consistent with this project's "start simple" bias.
"""

import asyncio

import pymupdf


class PdfExtractionError(Exception):
    pass


def _extract_text_sync(pdf_bytes: bytes) -> str:
    try:
        with pymupdf.open(stream=pdf_bytes, filetype="pdf") as doc:
            return "\n\n".join(page.get_text() for page in doc).strip()
    except pymupdf.FileDataError as e:
        raise PdfExtractionError(f"Could not parse PDF: {e}") from e


async def extract_text(pdf_bytes: bytes) -> str:
    """Returns the extracted text, or "" if the PDF has no extractable text
    (most likely a scanned/image-only PDF — needs OCR, not yet implemented).
    """
    return await asyncio.to_thread(_extract_text_sync, pdf_bytes)
