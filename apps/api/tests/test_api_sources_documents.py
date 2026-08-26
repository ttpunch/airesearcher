import uuid

import httpx
import pymupdf
import pytest
from asgi_lifespan import LifespanManager
from sqlalchemy import delete, select

from app.core.db import AsyncSessionLocal
from app.main import app
from app.models.document import Document
from app.models.source import Source


def _make_pdf(text: str) -> bytes:
    doc = pymupdf.open()
    doc.new_page().insert_text((72, 72), text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


@pytest.fixture
async def client(s3_env):
    async with LifespanManager(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            yield c


async def _cleanup_source(url: str) -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Source).where(Source.url == url))
        source = result.scalar_one_or_none()
        if source is not None:
            await db.execute(delete(Document).where(Document.source_id == source.id))
            await db.execute(delete(Source).where(Source.id == source.id))
            await db.commit()


async def test_create_and_list_source(client):
    # Distinct from app.core.seed's real BHEL URLs, which the app's lifespan
    # now seeds on every startup (including this test, via LifespanManager)
    # — using one of those here would collide on the url unique constraint.
    # Also unique per run, in case a previous run's cleanup didn't complete.
    payload = {
        "name": "BHEL Test Fixture Source",
        "url": f"https://www.bhel.com/test-fixture-source-{uuid.uuid4()}",
        "source_type": "bhel_official",
        "tier": "T1",
    }
    try:
        create_resp = await client.post("/api/sources", json=payload)
        assert create_resp.status_code == 201
        created = create_resp.json()
        assert created["name"] == payload["name"]
        assert created["tier"] == "T1"
        assert created["active"] is True

        list_resp = await client.get("/api/sources")
        assert list_resp.status_code == 200
        urls = [s["url"] for s in list_resp.json()]
        assert payload["url"] in urls
    finally:
        await _cleanup_source(payload["url"])


async def test_upload_pdf_creates_document_with_extracted_text(client):
    pdf_bytes = _make_pdf("Uploaded BHEL document for evidence testing")

    resp = await client.post(
        "/api/documents/upload",
        files={"file": ("test.pdf", pdf_bytes, "application/pdf")},
    )
    assert resp.status_code == 201
    document = resp.json()
    assert document["status"] == "extracted"
    assert document["mime_type"] == "application/pdf"

    sources_resp = await client.get("/api/sources")
    upload_source = next(s for s in sources_resp.json() if s["url"] == "internal://user-upload")
    assert upload_source["tier"] == "UP"

    docs_resp = await client.get("/api/documents", params={"source_id": upload_source["id"]})
    assert any(d["id"] == document["id"] for d in docs_resp.json())


async def test_process_endpoint_chunks_uploaded_document(client):
    # Long enough to produce multiple paragraphs/chunks, not just one.
    text = "Uploaded BHEL document for hybrid search testing.\n\n" * 40
    pdf_bytes = _make_pdf(text)

    upload_resp = await client.post(
        "/api/documents/upload",
        files={"file": ("test.pdf", pdf_bytes, "application/pdf")},
    )
    document_id = upload_resp.json()["id"]

    process_resp = await client.post(f"/api/documents/{document_id}/process")
    assert process_resp.status_code == 200
    body = process_resp.json()
    assert body["document_id"] == document_id
    assert body["status"] == "chunked"
    assert len(body["chunks"]) > 0
    assert "embedding" not in body["chunks"][0]

    # idempotent by default: calling again returns the same chunk ids
    again_resp = await client.post(f"/api/documents/{document_id}/process")
    assert [c["id"] for c in again_resp.json()["chunks"]] == [c["id"] for c in body["chunks"]]


async def test_process_endpoint_404_for_missing_document(client):
    resp = await client.post("/api/documents/999999999/process")
    assert resp.status_code == 404


async def test_upload_rejects_non_pdf(client):
    resp = await client.post(
        "/api/documents/upload",
        files={"file": ("test.txt", b"not a pdf", "text/plain")},
    )
    assert resp.status_code == 400
