from sqlalchemy import delete, or_, select

from app.core.db import AsyncSessionLocal
from app.core.seed import BHEL_SEED_SOURCES, seed_sources
from app.models.entity import Entity, Relationship
from app.models.source import Source


async def _cleanup_seed_sources() -> None:
    urls = [entry["url"] for entry in BHEL_SEED_SOURCES]
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Source.id).where(Source.url.in_(urls)))
        source_ids = [row[0] for row in result.all()]
        # Other tests in this suite spin up the app via LifespanManager,
        # which seeds KG entities (and relationships between them) pointing
        # at these sources (see app/core/seed.py's seed_entities) — delete
        # relationships, then entities, before the source delete below, or
        # each hits its own FK constraint in turn.
        if source_ids:
            result = await db.execute(select(Entity.id).where(Entity.source_id.in_(source_ids)))
            entity_ids = [row[0] for row in result.all()]
            if entity_ids:
                await db.execute(
                    delete(Relationship).where(
                        or_(Relationship.from_entity_id.in_(entity_ids), Relationship.to_entity_id.in_(entity_ids))
                    )
                )
                await db.execute(delete(Entity).where(Entity.id.in_(entity_ids)))
        await db.execute(delete(Source).where(Source.url.in_(urls)))
        await db.commit()


async def test_seed_sources_is_idempotent():
    await _cleanup_seed_sources()
    try:
        async with AsyncSessionLocal() as db:
            first_run = await seed_sources(db)
            assert first_run == len(BHEL_SEED_SOURCES)

        async with AsyncSessionLocal() as db:
            second_run = await seed_sources(db)
            assert second_run == 0

            result = await db.execute(select(Source).where(Source.tier == "T1"))
            urls = {s.url for s in result.scalars().all()}
            for entry in BHEL_SEED_SOURCES:
                assert entry["url"] in urls
    finally:
        await _cleanup_seed_sources()
