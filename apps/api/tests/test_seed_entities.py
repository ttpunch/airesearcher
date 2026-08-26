from sqlalchemy import delete, select

from app.core.db import AsyncSessionLocal
from app.core.seed import (
    BHEL_SEED_SOURCES,
    COMPETITOR_SEED_SOURCES,
    TECHNOLOGY_ENTITIES,
    seed_competitor_sources,
    seed_entities,
    seed_sources,
)
from app.models.entity import Entity, Relationship
from app.models.source import Source


async def _cleanup() -> None:
    async with AsyncSessionLocal() as db:
        await db.execute(delete(Relationship))
        await db.execute(delete(Entity))
        urls = [e["url"] for e in BHEL_SEED_SOURCES] + [e["url"] for e in COMPETITOR_SEED_SOURCES]
        await db.execute(delete(Source).where(Source.url.in_(urls)))
        await db.commit()


async def test_seed_competitor_sources_is_idempotent():
    await _cleanup()
    try:
        async with AsyncSessionLocal() as db:
            first_run = await seed_competitor_sources(db)
            assert first_run == len(COMPETITOR_SEED_SOURCES)

        async with AsyncSessionLocal() as db:
            second_run = await seed_competitor_sources(db)
            assert second_run == 0
    finally:
        await _cleanup()


async def test_seed_entities_creates_bhel_competitors_and_technologies():
    await _cleanup()
    try:
        async with AsyncSessionLocal() as db:
            await seed_sources(db)
            await seed_competitor_sources(db)
            inserted = await seed_entities(db)
            assert inserted > 0

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Entity).where(Entity.entity_type == "organization"))
            bhel_entities = result.scalars().all()
            assert any(e.name == "BHEL" for e in bhel_entities)
            bhel = next(e for e in bhel_entities if e.name == "BHEL")
            assert bhel.source_id is not None

            result = await db.execute(select(Entity).where(Entity.entity_type == "competitor"))
            competitor_names = {e.name for e in result.scalars().all()}
            assert competitor_names == {c["name"] for c in COMPETITOR_SEED_SOURCES}

            result = await db.execute(select(Entity).where(Entity.entity_type == "technology"))
            tech_entities = result.scalars().all()
            assert {e.name for e in tech_entities} == {t["name"] for t in TECHNOLOGY_ENTITIES}
            assert all(e.source_id is None for e in tech_entities)

            result = await db.execute(select(Relationship).where(Relationship.relation_type == "competes_with"))
            competes_rels = result.scalars().all()
            assert len(competes_rels) == len(COMPETITOR_SEED_SOURCES)
    finally:
        await _cleanup()


async def test_seed_entities_is_idempotent():
    await _cleanup()
    try:
        async with AsyncSessionLocal() as db:
            await seed_sources(db)
            await seed_competitor_sources(db)
            await seed_entities(db)

        async with AsyncSessionLocal() as db:
            second_run = await seed_entities(db)
            assert second_run == 0
    finally:
        await _cleanup()
