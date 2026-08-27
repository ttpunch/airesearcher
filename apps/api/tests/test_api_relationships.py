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


async def test_list_relationships_includes_seeded_competes_with_edges(client):
    resp = await client.get("/api/relationships")
    assert resp.status_code == 200
    relationships = resp.json()
    assert len(relationships) >= 8  # 4 competes_with + 4 relevant_to

    competes = [r for r in relationships if r["relation_type"] == "competes_with"]
    assert any(r["from_entity_name"] == "BHEL" and r["to_entity_name"] == "Siemens Energy" for r in competes)

    relevant = [r for r in relationships if r["relation_type"] == "relevant_to"]
    assert any(r["from_entity_name"] == "Digital Twin" and r["to_entity_name"] == "BHEL" for r in relevant)
