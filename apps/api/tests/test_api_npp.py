"""API-level tests for POST /api/npp/sync and GET /api/npp/status —
LifespanManager + ASGITransport, same harness as test_api_tenders.py.
get_npp_client is overridden so the real network is never touched.
"""

import json
import uuid
from pathlib import Path

import httpx
import pytest
from asgi_lifespan import LifespanManager
from sqlalchemy import delete

from app.core.config import settings
from app.core.db import AsyncSessionLocal
from app.main import app
from app.models.entity import Entity, Relationship
from app.models.source import Source
from app.portals.npp.client import NppClient
from app.portals.npp.ingest import NPP_SOURCE_NAME
from app.routers.npp import get_npp_client

FIXTURES = Path(__file__).parent / "fixtures" / "npp"
BMAP_DATA = json.loads((FIXTURES / "get_bmap_data.json").read_text())
ALL_ZONE = json.loads((FIXTURES / "get_all_zone.json").read_text())


def _handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/robots.txt":
        return httpx.Response(404)
    if request.url.path == "/dashBoard/getBMapData":
        return httpx.Response(200, json=BMAP_DATA)
    if request.url.path == "/dashBoard/getAllZone":
        return httpx.Response(200, json=ALL_ZONE)
    return httpx.Response(404)


def make_test_client() -> NppClient:
    base_url = f"https://npp-test-{uuid.uuid4().hex}.example"
    http_client = httpx.AsyncClient(transport=httpx.MockTransport(_handler), base_url=base_url)
    return NppClient(base_url=base_url, client=http_client)


@pytest.fixture
async def client():
    app.dependency_overrides[get_npp_client] = make_test_client
    try:
        async with LifespanManager(app):
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
                yield c
    finally:
        app.dependency_overrides.pop(get_npp_client, None)


async def _cleanup() -> None:
    async with AsyncSessionLocal() as db:
        await db.execute(
            delete(Relationship).where(Relationship.relation_type == "developed_by")
        )
        await db.execute(delete(Entity).where(Entity.entity_type.in_(["power_organization", "power_project"])))
        await db.execute(delete(Source).where(Source.name == NPP_SOURCE_NAME))
        await db.commit()


async def test_sync_endpoint_returns_counts(client):
    await _cleanup()
    try:
        response = await client.post("/api/npp/sync")
        assert response.status_code == 200
        body = response.json()
        assert body["source_created"] is True
        assert body["organizations_created"] > 0
        assert body["projects_created"] > 0
    finally:
        await _cleanup()


async def test_sync_endpoint_is_idempotent(client):
    await _cleanup()
    try:
        await client.post("/api/npp/sync")
        second = await client.post("/api/npp/sync")
        assert second.status_code == 200
        body = second.json()
        assert body["source_created"] is False
        assert body["organizations_created"] == 0
        assert body["projects_created"] == 0
    finally:
        await _cleanup()


async def test_status_endpoint_reflects_sync_state(client):
    await _cleanup()
    try:
        before = await client.get("/api/npp/status")
        assert before.status_code == 200
        assert before.json()["synced"] is False

        await client.post("/api/npp/sync")

        after = await client.get("/api/npp/status")
        body = after.json()
        assert body["synced"] is True
        assert body["last_synced_at"] is not None
        assert body["power_organizations"] > 0
        assert body["power_projects"] > 0
    finally:
        await _cleanup()


async def test_capacity_snapshot_endpoint_returns_live_fields(client):
    response = await client.get("/api/npp/capacity-snapshot")
    assert response.status_code == 200
    body = response.json()
    assert body["installed_capacity_mw"] == ALL_ZONE["monthlyAllIndiaGen"]["installed_capacity"]
    assert len(body["by_sector"]) == len(ALL_ZONE["installed_Capacity_List"])
    assert body["retrieved_at"] is not None
    assert body["source_endpoint"].endswith("/dashBoard/getAllZone")


async def test_capacity_snapshot_endpoint_disabled_returns_503(client):
    original = settings.npp_enabled
    settings.npp_enabled = False
    try:
        response = await client.get("/api/npp/capacity-snapshot")
        assert response.status_code == 503
    finally:
        settings.npp_enabled = original


async def test_sync_endpoint_disabled_returns_503(client):
    await _cleanup()
    original = settings.npp_enabled
    settings.npp_enabled = False
    try:
        response = await client.post("/api/npp/sync")
        assert response.status_code == 503
    finally:
        settings.npp_enabled = original
        await _cleanup()


async def test_ingested_entities_are_visible_via_entities_api(client):
    await _cleanup()
    try:
        await client.post("/api/npp/sync")
        response = await client.get("/api/entities", params={"entity_type": "power_project"})
        assert response.status_code == 200
        names = {e["name"] for e in response.json()}
        assert "Amarkantak TPP Expansion" in names
    finally:
        await _cleanup()
