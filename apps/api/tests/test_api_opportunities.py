import uuid

import httpx
import pytest
from asgi_lifespan import LifespanManager
from sqlalchemy import delete

from app.core.db import AsyncSessionLocal
from app.main import app
from app.models.opportunity import Opportunity


@pytest.fixture
async def client(s3_env):
    async with LifespanManager(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            yield c


async def _make_opportunity() -> int:
    async with AsyncSessionLocal() as db:
        opportunity = Opportunity(
            title=f"API test fixture opportunity {uuid.uuid4()}",
            description="A fixture opportunity for API tests — not one of the seeded Top 10.",
            feasibility="A",
            strategic_value="Medium",
            weighted_score=5,
            tech_summary="Test tech.",
            timeline="1wk",
            risk="None.",
            source_section="test-fixture",
        )
        db.add(opportunity)
        await db.commit()
        await db.refresh(opportunity)
        return opportunity.id


async def _cleanup(opportunity_id: int) -> None:
    async with AsyncSessionLocal() as db:
        await db.execute(delete(Opportunity).where(Opportunity.id == opportunity_id))
        await db.commit()


async def test_list_opportunities_returns_seeded_top_10_ordered_by_score(client):
    resp = await client.get("/api/opportunities")
    assert resp.status_code == 200
    opportunities = resp.json()
    assert len(opportunities) >= 10

    scores = [o["weighted_score"] for o in opportunities]
    assert scores == sorted(scores, reverse=True)

    top = next(o for o in opportunities if o["title"] == "BHEL Public Research Assistant (Q&A + evidence chain)")
    assert top["weighted_score"] == 13
    assert top["status"] == "proposed"


async def test_filter_opportunities_by_status(client):
    resp = await client.get("/api/opportunities", params={"status": "proposed"})
    assert resp.status_code == 200
    assert all(o["status"] == "proposed" for o in resp.json())


async def test_get_missing_opportunity_404(client):
    resp = await client.get("/api/opportunities/999999999")
    assert resp.status_code == 404


async def test_approve_opportunity_sets_status_and_approver(client):
    opportunity_id = await _make_opportunity()
    try:
        resp = await client.post(f"/api/opportunities/{opportunity_id}/approve", json={"approved_by": "Test CTO"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "approved"
        assert body["approved_by"] == "Test CTO"
        assert body["approved_at"] is not None
    finally:
        await _cleanup(opportunity_id)


async def test_reject_opportunity_sets_status_and_approver(client):
    opportunity_id = await _make_opportunity()
    try:
        resp = await client.post(f"/api/opportunities/{opportunity_id}/reject", json={"approved_by": "Test CTO"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "rejected"
        assert body["approved_by"] == "Test CTO"
    finally:
        await _cleanup(opportunity_id)


async def test_cannot_re_decide_an_already_decided_opportunity(client):
    opportunity_id = await _make_opportunity()
    try:
        first = await client.post(f"/api/opportunities/{opportunity_id}/approve", json={"approved_by": "First"})
        assert first.status_code == 200

        second = await client.post(f"/api/opportunities/{opportunity_id}/reject", json={"approved_by": "Second"})
        assert second.status_code == 409
    finally:
        await _cleanup(opportunity_id)


async def test_approve_rejects_empty_approver_name(client):
    opportunity_id = await _make_opportunity()
    try:
        resp = await client.post(f"/api/opportunities/{opportunity_id}/approve", json={"approved_by": "   "})
        assert resp.status_code == 400
    finally:
        await _cleanup(opportunity_id)


async def test_decide_on_missing_opportunity_404(client):
    resp = await client.post("/api/opportunities/999999999/approve", json={"approved_by": "Someone"})
    assert resp.status_code == 404
