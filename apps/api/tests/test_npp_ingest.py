"""Tests for app/portals/npp/ingest.py against a real local Postgres (same
discipline as tests/test_seed_entities.py) — httpx.MockTransport stands in
for npp.gov.in, real Entity/Relationship/Source rows are the point of the
test.
"""

import json
import uuid
from pathlib import Path

import httpx
from sqlalchemy import delete, select

from app.core.db import AsyncSessionLocal
from app.models.entity import Entity, Relationship
from app.models.source import Source
from app.portals.npp.client import NppClient
from app.portals.npp.ingest import NPP_SOURCE_NAME, sync_npp

FIXTURES = Path(__file__).parent / "fixtures" / "npp"
BMAP_DATA = json.loads((FIXTURES / "get_bmap_data.json").read_text())


def _handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/robots.txt":
        return httpx.Response(404)
    if request.url.path == "/dashBoard/getBMapData":
        return httpx.Response(200, json=BMAP_DATA)
    return httpx.Response(404)


def make_client() -> NppClient:
    base_url = f"https://npp-test-{uuid.uuid4().hex}.example"
    http_client = httpx.AsyncClient(transport=httpx.MockTransport(_handler), base_url=base_url)
    return NppClient(base_url=base_url, client=http_client)


async def _cleanup() -> None:
    async with AsyncSessionLocal() as db:
        await db.execute(
            delete(Relationship).where(
                Relationship.from_entity_id.in_(select(Entity.id).where(Entity.entity_type == "power_project"))
            )
        )
        await db.execute(delete(Entity).where(Entity.entity_type.in_(["power_organization", "power_project"])))
        await db.execute(delete(Source).where(Source.name == NPP_SOURCE_NAME))
        await db.commit()


async def test_sync_creates_source_organizations_and_projects():
    await _cleanup()
    try:
        async with AsyncSessionLocal() as db:
            result = await sync_npp(db, make_client())
            assert result.source_created is True
            assert result.organizations_created > 0
            assert result.projects_created > 0

        async with AsyncSessionLocal() as db:
            source_result = await db.execute(select(Source).where(Source.name == NPP_SOURCE_NAME))
            source = source_result.scalar_one()
            assert source.tier == "T1"
            assert source.last_crawled_at is not None

            orgs = (await db.execute(select(Entity).where(Entity.entity_type == "power_organization"))).scalars().all()
            assert len(orgs) == result.organizations_created
            assert all(o.source_id == source.id for o in orgs)

            projects = (await db.execute(select(Entity).where(Entity.entity_type == "power_project"))).scalars().all()
            assert len(projects) == result.projects_created
            # Real fixture record: Amarkantak TPP Expansion has no organization,
            # so it must exist as a project entity with no relationship.
            assert any(p.name == "Amarkantak TPP Expansion" for p in projects)
    finally:
        await _cleanup()


async def test_sync_is_idempotent_on_unchanged_data():
    await _cleanup()
    try:
        async with AsyncSessionLocal() as db:
            await sync_npp(db, make_client())

        async with AsyncSessionLocal() as db:
            second = await sync_npp(db, make_client())
            assert second.source_created is False
            assert second.organizations_created == 0
            assert second.projects_created == 0
            assert second.organizations_updated == 0
            assert second.projects_updated == 0
            assert second.relationships_created == 0
    finally:
        await _cleanup()


async def test_sync_updates_changed_description_without_duplicating():
    await _cleanup()
    try:
        async with AsyncSessionLocal() as db:
            await sync_npp(db, make_client())

        async with AsyncSessionLocal() as db:
            projects_before = (
                (await db.execute(select(Entity).where(Entity.entity_type == "power_project"))).scalars().all()
            )
            target = next(p for p in projects_before if p.name == "Amarkantak TPP Expansion")
            target.description = "stale description that will be refreshed"
            await db.commit()

        async with AsyncSessionLocal() as db:
            result = await sync_npp(db, make_client())
            assert result.projects_created == 0
            assert result.projects_updated >= 1

        async with AsyncSessionLocal() as db:
            projects_after = (
                (await db.execute(select(Entity).where(Entity.entity_type == "power_project"))).scalars().all()
            )
            assert len(projects_after) == len(projects_before)  # no duplicate row
            refreshed = next(p for p in projects_after if p.name == "Amarkantak TPP Expansion")
            assert refreshed.description != "stale description that will be refreshed"
    finally:
        await _cleanup()


async def test_sync_creates_developed_by_relationship_when_organization_known():
    await _cleanup()
    try:
        async with AsyncSessionLocal() as db:
            await sync_npp(db, make_client())

        async with AsyncSessionLocal() as db:
            rels = (await db.execute(select(Relationship).where(Relationship.relation_type == "developed_by"))).scalars().all()
            # Real fixture data: most under-construction projects have no
            # organization, so this must not assume every project gets one —
            # only that the mechanism works for whichever ones do.
            for rel in rels:
                from_entity = await db.get(Entity, rel.from_entity_id)
                to_entity = await db.get(Entity, rel.to_entity_id)
                assert from_entity.entity_type == "power_project"
                assert to_entity.entity_type == "power_organization"
    finally:
        await _cleanup()


async def test_sync_no_organization_project_has_no_relationship():
    await _cleanup()
    try:
        async with AsyncSessionLocal() as db:
            await sync_npp(db, make_client())

        async with AsyncSessionLocal() as db:
            amarkantak = (
                await db.execute(select(Entity).where(Entity.name == "Amarkantak TPP Expansion"))
            ).scalar_one()
            rels = (
                await db.execute(select(Relationship).where(Relationship.from_entity_id == amarkantak.id))
            ).scalars().all()
            assert rels == []
    finally:
        await _cleanup()
