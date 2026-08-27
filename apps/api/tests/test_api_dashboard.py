import httpx
import pytest
from asgi_lifespan import LifespanManager

from app.main import app


@pytest.fixture
async def client(s3_env):
    async with LifespanManager(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            yield c


async def test_dashboard_summary_counts_reflect_seeded_data(client):
    resp = await client.get("/api/dashboard/summary")
    assert resp.status_code == 200
    body = resp.json()

    counts = body["counts"]
    assert counts["sources"] >= 9  # 5 BHEL + 4 competitor seeds
    assert counts["entities"] >= 9  # BHEL + 4 competitors + 4 technologies
    assert counts["opportunities"] >= 10  # the seeded Top 10

    assert len(body["top_opportunities"]) == 5
    scores = [o["weighted_score"] for o in body["top_opportunities"]]
    assert scores == sorted(scores, reverse=True)
    assert body["top_opportunities"][0]["title"] == "BHEL Public Research Assistant (Q&A + evidence chain)"
