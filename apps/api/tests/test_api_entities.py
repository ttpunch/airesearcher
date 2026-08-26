import uuid

import httpx
import pytest
from asgi_lifespan import LifespanManager
from sqlalchemy import delete, or_

from app.core.db import AsyncSessionLocal
from app.main import app
from app.models.entity import Entity, Relationship


@pytest.fixture
async def client(s3_env):
    async with LifespanManager(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            yield c


async def _cleanup(entity_ids: list[int]) -> None:
    async with AsyncSessionLocal() as db:
        await db.execute(
            delete(Relationship).where(
                or_(Relationship.from_entity_id.in_(entity_ids), Relationship.to_entity_id.in_(entity_ids))
            )
        )
        await db.execute(delete(Entity).where(Entity.id.in_(entity_ids)))
        await db.commit()


async def test_seeded_bhel_and_competitor_entities_are_listed(client):
    resp = await client.get("/api/entities")
    assert resp.status_code == 200
    entities = resp.json()

    names_by_type: dict[str, set[str]] = {}
    for e in entities:
        names_by_type.setdefault(e["entity_type"], set()).add(e["name"])

    assert "BHEL" in names_by_type.get("organization", set())
    assert "Siemens Energy" in names_by_type.get("competitor", set())
    assert "Digital Twin" in names_by_type.get("technology", set())


async def test_competitor_entity_carries_source_attribution(client):
    resp = await client.get("/api/entities", params={"entity_type": "competitor"})
    assert resp.status_code == 200
    siemens = next(e for e in resp.json() if e["name"] == "Siemens Energy")
    assert siemens["source_url"] == "https://www.siemens-energy.com/global/en/home.html"
    assert siemens["source_name"] == "Siemens Energy"


async def test_technology_entity_has_no_source(client):
    resp = await client.get("/api/entities", params={"entity_type": "technology"})
    assert resp.status_code == 200
    digital_twin = next(e for e in resp.json() if e["name"] == "Digital Twin")
    assert digital_twin["source_url"] is None
    assert digital_twin["source_id"] is None


async def test_filter_entities_by_type(client):
    resp = await client.get("/api/entities", params={"entity_type": "technology"})
    assert resp.status_code == 200
    entities = resp.json()
    assert len(entities) > 0
    assert all(e["entity_type"] == "technology" for e in entities)


async def test_get_entity_detail_includes_relationships(client):
    list_resp = await client.get("/api/entities", params={"entity_type": "organization"})
    bhel = next(e for e in list_resp.json() if e["name"] == "BHEL")

    detail_resp = await client.get(f"/api/entities/{bhel['id']}")
    assert detail_resp.status_code == 200
    body = detail_resp.json()
    assert body["name"] == "BHEL"
    assert len(body["relationships"]) > 0
    assert any(r["relation_type"] == "competes_with" for r in body["relationships"])


async def test_get_missing_entity_404(client):
    resp = await client.get("/api/entities/999999999")
    assert resp.status_code == 404


async def test_create_entity(client):
    payload = {
        "name": f"Test Manual Entity {uuid.uuid4()}",
        "entity_type": "technology",
        "description": "Created directly via the API for a test.",
    }
    resp = await client.post("/api/entities", json=payload)
    assert resp.status_code == 201
    created = resp.json()
    try:
        assert created["name"] == payload["name"]
        assert created["source_id"] is None
    finally:
        await _cleanup([created["id"]])
