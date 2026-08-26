from sqlalchemy import delete, select

from app.core.db import AsyncSessionLocal
from app.core.seed import BHEL_SEED_SOURCES, seed_sources
from app.models.source import Source


async def _cleanup_seed_sources() -> None:
    urls = [entry["url"] for entry in BHEL_SEED_SOURCES]
    async with AsyncSessionLocal() as db:
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
