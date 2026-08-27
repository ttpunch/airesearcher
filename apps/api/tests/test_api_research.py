"""API-level tests for POST /api/research and its retrieval endpoints.

Overrides get_research_runner so the real claude_agent_sdk.query() is
never on the call path here — same reasoning as test_deep_research.py.
"""

import httpx
import pytest
from asgi_lifespan import LifespanManager
from sqlalchemy import delete

from app.agent.deep_research import DeepResearchResult
from app.agent.multi_citations import VerifiedReference
from app.core.db import AsyncSessionLocal
from app.main import app
from app.models.research_report import ResearchReport
from app.routers.research import get_research_runner


@pytest.fixture
async def client(s3_env):
    async with LifespanManager(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            yield c
    app.dependency_overrides.pop(get_research_runner, None)


async def _cleanup(report_id: int) -> None:
    async with AsyncSessionLocal() as db:
        await db.execute(delete(ResearchReport).where(ResearchReport.id == report_id))
        await db.commit()


async def _stub_multi_type_result(db, topic, embedding_provider):
    return DeepResearchResult(
        summary="BHEL competes with Siemens Energy [FACT] [entity:1]. A relevant tender is open [FACT] [tender:2].",
        references=[
            VerifiedReference(
                ref_type="entity", ref_id=1, label="Siemens Energy", detail=None, url="https://www.siemens-energy.com/", tier=None
            ),
            VerifiedReference(
                ref_type="tender", ref_id=2, label="Boiler Tender", detail="BHEL — open", url="https://www.bhel.com/tenders/2", tier=None
            ),
        ],
        unverifiable_reference_count=0,
    )


async def _stub_no_evidence_result(db, topic, embedding_provider):
    return DeepResearchResult(summary="I cannot verify this from public sources.", references=[], unverifiable_reference_count=0)


async def test_create_report_persists_and_returns_multi_type_references(client):
    app.dependency_overrides[get_research_runner] = lambda: _stub_multi_type_result

    resp = await client.post("/api/research", json={"topic": "BHEL vs Siemens Energy"})
    assert resp.status_code == 201
    body = resp.json()
    try:
        assert body["status"] == "completed"
        assert body["unverifiable_reference_count"] == 0
        ref_types = {r["ref_type"] for r in body["references"]}
        assert ref_types == {"entity", "tender"}

        get_resp = await client.get(f"/api/research/{body['id']}")
        assert get_resp.status_code == 200
        assert get_resp.json()["topic"] == "BHEL vs Siemens Energy"
    finally:
        await _cleanup(body["id"])


async def test_create_report_no_evidence_status(client):
    app.dependency_overrides[get_research_runner] = lambda: _stub_no_evidence_result

    resp = await client.post("/api/research", json={"topic": "Something unresearchable"})
    assert resp.status_code == 201
    body = resp.json()
    try:
        assert body["status"] == "no_evidence"
        assert body["references"] == []
    finally:
        await _cleanup(body["id"])


async def test_create_report_rejects_empty_topic(client):
    resp = await client.post("/api/research", json={"topic": "   "})
    assert resp.status_code == 400


async def test_get_missing_report_404(client):
    resp = await client.get("/api/research/999999999")
    assert resp.status_code == 404


async def test_list_reports_includes_created_report(client):
    app.dependency_overrides[get_research_runner] = lambda: _stub_multi_type_result

    resp = await client.post("/api/research", json={"topic": "List fixture topic"})
    report_id = resp.json()["id"]
    try:
        list_resp = await client.get("/api/research")
        assert list_resp.status_code == 200
        assert any(r["id"] == report_id for r in list_resp.json())
    finally:
        await _cleanup(report_id)
