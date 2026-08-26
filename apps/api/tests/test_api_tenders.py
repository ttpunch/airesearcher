import uuid

import httpx
import pytest
from asgi_lifespan import LifespanManager
from sqlalchemy import delete

from app.core.db import AsyncSessionLocal
from app.main import app
from app.models.document import Document
from app.models.source import Source
from app.models.tender import Tender


@pytest.fixture
async def client(s3_env):
    async with LifespanManager(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            yield c


async def _make_source() -> int:
    async with AsyncSessionLocal() as db:
        source = Source(
            name="Tender API test source",
            url=f"internal://tender-api-test-{uuid.uuid4()}",
            source_type="tender_portal",
            tier="T1",
        )
        db.add(source)
        await db.commit()
        await db.refresh(source)
        return source.id


async def _cleanup(source_id: int, document_id: int | None = None) -> None:
    async with AsyncSessionLocal() as db:
        await db.execute(delete(Tender).where(Tender.source_id == source_id))
        if document_id is not None:
            await db.execute(delete(Document).where(Document.id == document_id))
        await db.execute(delete(Source).where(Source.id == source_id))
        await db.commit()


async def test_create_and_get_tender(client):
    source_id = await _make_source()
    payload = {
        "source_id": source_id,
        "title": "Supply of Turbine Blades",
        "tender_ref": "BHEL/T/001",
        "organization": "BHEL",
        "url": "https://www.bhel.com/tenders/example",
        "status": "open",
    }
    try:
        create_resp = await client.post("/api/tenders", json=payload)
        assert create_resp.status_code == 201
        created = create_resp.json()
        assert created["title"] == payload["title"]
        assert created["extracted_requirements"] is None

        get_resp = await client.get(f"/api/tenders/{created['id']}")
        assert get_resp.status_code == 200
        assert get_resp.json()["organization"] == "BHEL"
    finally:
        await _cleanup(source_id)


async def test_get_missing_tender_404(client):
    resp = await client.get("/api/tenders/999999999")
    assert resp.status_code == 404


async def test_list_tenders_filters_by_status_and_organization(client):
    source_id = await _make_source()
    try:
        for i, (status, org) in enumerate([("open", "BHEL"), ("closed", "BHEL"), ("open", "L&T")]):
            resp = await client.post(
                "/api/tenders",
                json={
                    "source_id": source_id,
                    "title": f"Tender {i}",
                    "organization": org,
                    "url": f"https://example.com/tender-{i}-{uuid.uuid4()}",
                    "status": status,
                },
            )
            assert resp.status_code == 201

        open_resp = await client.get("/api/tenders", params={"status": "open"})
        open_tenders = [t for t in open_resp.json() if t["source_id"] == source_id]
        assert len(open_tenders) == 2

        bhel_resp = await client.get("/api/tenders", params={"organization": "BHEL"})
        bhel_tenders = [t for t in bhel_resp.json() if t["source_id"] == source_id]
        assert len(bhel_tenders) == 2
    finally:
        await _cleanup(source_id)


async def test_analyze_aggregates_by_status_and_organization(client):
    source_id = await _make_source()
    try:
        for status, org in [("open", "BHEL"), ("open", "BHEL"), ("awarded", "BHEL")]:
            resp = await client.post(
                "/api/tenders",
                json={
                    "source_id": source_id,
                    "title": "Analysis fixture tender",
                    "organization": org,
                    "url": f"https://example.com/analysis-{uuid.uuid4()}",
                    "status": status,
                },
            )
            assert resp.status_code == 201

        analysis_resp = await client.get("/api/tenders/analyze")
        assert analysis_resp.status_code == 200
        body = analysis_resp.json()
        assert body["total_tenders"] >= 3

        bhel_row = next(row for row in body["by_organization"] if row["organization"] == "BHEL")
        assert bhel_row["total"] >= 3
        assert bhel_row["by_status"]["open"] >= 2
        assert bhel_row["by_status"]["awarded"] >= 1
    finally:
        await _cleanup(source_id)


async def test_extract_requirements_from_linked_document(client):
    source_id = await _make_source()
    document_id = None
    try:
        async with AsyncSessionLocal() as db:
            document = Document(
                source_id=source_id,
                url=None,
                content_hash="tender-extract-test",
                storage_path="test/tender",
                mime_type="text/plain",
                status="extracted",
                extracted_text=(
                    "Tender No: BHEL/X/2026/0099\n\n"
                    "Last date for submission: 01-Apr-2026\n\n"
                    "EMD: Rs. 1,00,000\n\n"
                    "Eligibility criteria: Bidders shall have experience of similar works."
                ),
            )
            db.add(document)
            await db.commit()
            await db.refresh(document)
            document_id = document.id

        create_resp = await client.post(
            "/api/tenders",
            json={
                "source_id": source_id,
                "document_id": document_id,
                "title": "Extraction fixture tender",
                "organization": "BHEL",
                "url": "https://www.bhel.com/tenders/extraction-fixture",
            },
        )
        tender_id = create_resp.json()["id"]

        extract_resp = await client.post(f"/api/tenders/{tender_id}/extract")
        assert extract_resp.status_code == 200
        body = extract_resp.json()
        assert body["tender_ref"] == "BHEL/X/2026/0099"
        assert body["closing_date_text"] == "01-Apr-2026"
        assert body["emd_amount_text"] == "1,00,000"
        assert len(body["eligibility_snippets"]) >= 1

        get_resp = await client.get(f"/api/tenders/{tender_id}")
        assert get_resp.json()["extracted_requirements"] is not None
    finally:
        await _cleanup(source_id, document_id)


async def test_extract_requirements_without_linked_document_422(client):
    source_id = await _make_source()
    try:
        create_resp = await client.post(
            "/api/tenders",
            json={
                "source_id": source_id,
                "title": "No document tender",
                "organization": "BHEL",
                "url": "https://www.bhel.com/tenders/no-document",
            },
        )
        tender_id = create_resp.json()["id"]

        extract_resp = await client.post(f"/api/tenders/{tender_id}/extract")
        assert extract_resp.status_code == 422
    finally:
        await _cleanup(source_id)
