import json
import uuid

import pytest
from sqlalchemy import delete

from app.agent.deep_research_tools import (
    make_search_entities_tool,
    make_search_tenders_tool,
)
from app.core.db import AsyncSessionLocal
from app.models.entity import Entity
from app.models.source import Source
from app.models.tender import Tender


@pytest.fixture
async def indexed_tender():
    async with AsyncSessionLocal() as db:
        source = Source(
            name="Deep research tender test source",
            url=f"internal://deep-research-tender-test-{uuid.uuid4()}",
            source_type="tender_portal",
            tier="T1",
        )
        db.add(source)
        await db.commit()
        await db.refresh(source)

        tender = Tender(
            source_id=source.id,
            title="Deep Research Fixture Tender for Boiler Parts",
            organization="BHEL",
            url="https://www.bhel.com/tenders/deep-research-fixture",
            status="open",
        )
        db.add(tender)
        await db.commit()
        await db.refresh(tender)

        yield db, tender, source

        await db.execute(delete(Tender).where(Tender.id == tender.id))
        await db.execute(delete(Source).where(Source.id == source.id))
        await db.commit()


@pytest.fixture
async def indexed_entity():
    async with AsyncSessionLocal() as db:
        entity = Entity(
            name=f"Deep Research Fixture Entity {uuid.uuid4()}",
            entity_type="technology",
            description="A fixture technology entity for deep-research tool tests.",
        )
        db.add(entity)
        await db.commit()
        await db.refresh(entity)

        yield db, entity

        await db.execute(delete(Entity).where(Entity.id == entity.id))
        await db.commit()


async def test_search_tenders_tool_returns_real_results_and_records_ids(indexed_tender):
    db, tender, _source = indexed_tender
    retrieved_tender_ids: set[int] = set()
    search_tool = make_search_tenders_tool(db, retrieved_tender_ids)

    result = await search_tool.handler({"query": "Boiler Parts", "limit": 5})
    payload = json.loads(result["content"][0]["text"])

    assert any(item["tender_id"] == tender.id for item in payload)
    matching = next(item for item in payload if item["tender_id"] == tender.id)
    assert matching["organization"] == "BHEL"
    assert matching["status"] == "open"
    assert tender.id in retrieved_tender_ids


async def test_search_tenders_tool_no_results_message():
    async with AsyncSessionLocal() as db:
        retrieved_tender_ids: set[int] = set()
        search_tool = make_search_tenders_tool(db, retrieved_tender_ids)
        result = await search_tool.handler({"query": f"nonsense-{uuid.uuid4()}", "limit": 5})
        assert "No matching tenders found" in result["content"][0]["text"]
        assert retrieved_tender_ids == set()


async def test_search_entities_tool_returns_real_results_and_records_ids(indexed_entity):
    db, entity = indexed_entity
    retrieved_entity_ids: set[int] = set()
    search_tool = make_search_entities_tool(db, retrieved_entity_ids)

    result = await search_tool.handler({"query": "Deep Research Fixture Entity", "limit": 5})
    payload = json.loads(result["content"][0]["text"])

    assert any(item["entity_id"] == entity.id for item in payload)
    matching = next(item for item in payload if item["entity_id"] == entity.id)
    assert matching["entity_type"] == "technology"
    assert entity.id in retrieved_entity_ids


async def test_search_entities_tool_includes_source_url_when_present():
    async with AsyncSessionLocal() as db:
        source = Source(
            name="Entity tool source test",
            url=f"internal://entity-tool-source-{uuid.uuid4()}",
            source_type="test",
            tier="T1",
        )
        db.add(source)
        await db.commit()
        await db.refresh(source)

        entity = Entity(
            name=f"Sourced Entity {uuid.uuid4()}", entity_type="competitor", source_id=source.id
        )
        db.add(entity)
        await db.commit()
        await db.refresh(entity)

        try:
            retrieved_entity_ids: set[int] = set()
            search_tool = make_search_entities_tool(db, retrieved_entity_ids)
            result = await search_tool.handler({"query": entity.name, "limit": 5})
            payload = json.loads(result["content"][0]["text"])
            matching = next(item for item in payload if item["entity_id"] == entity.id)
            assert matching["source_url"] == source.url
        finally:
            await db.execute(delete(Entity).where(Entity.id == entity.id))
            await db.execute(delete(Source).where(Source.id == source.id))
            await db.commit()


async def test_search_entities_tool_no_results_message():
    async with AsyncSessionLocal() as db:
        retrieved_entity_ids: set[int] = set()
        search_tool = make_search_entities_tool(db, retrieved_entity_ids)
        result = await search_tool.handler({"query": f"nonsense-{uuid.uuid4()}", "limit": 5})
        assert "No matching entities found" in result["content"][0]["text"]
        assert retrieved_entity_ids == set()
