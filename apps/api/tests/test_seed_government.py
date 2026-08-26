from sqlalchemy import delete, select

from app.core.db import AsyncSessionLocal
from app.core.seed import (
    GEM_SEED_TENDERS,
    GOVERNMENT_SEED_SOURCES,
    seed_gem_tenders,
    seed_government_sources,
)
from app.models.source import Source
from app.models.tender import Tender


async def _cleanup() -> None:
    async with AsyncSessionLocal() as db:
        refs = [t["tender_ref"] for t in GEM_SEED_TENDERS]
        await db.execute(delete(Tender).where(Tender.tender_ref.in_(refs)))
        urls = [s["url"] for s in GOVERNMENT_SEED_SOURCES]
        await db.execute(delete(Source).where(Source.url.in_(urls)))
        await db.commit()


async def test_seed_government_sources_is_idempotent():
    await _cleanup()
    try:
        async with AsyncSessionLocal() as db:
            first_run = await seed_government_sources(db)
            assert first_run == len(GOVERNMENT_SEED_SOURCES)

        async with AsyncSessionLocal() as db:
            second_run = await seed_government_sources(db)
            assert second_run == 0

            result = await db.execute(select(Source).where(Source.url == "https://gem.gov.in/"))
            gem_source = result.scalar_one()
            assert gem_source.tier == "T1"
            assert gem_source.source_type == "tender_portal"
    finally:
        await _cleanup()


async def test_seed_gem_tenders_creates_real_bid_records_linked_to_gem_source():
    await _cleanup()
    try:
        async with AsyncSessionLocal() as db:
            await seed_government_sources(db)
            inserted = await seed_gem_tenders(db)
            assert inserted == len(GEM_SEED_TENDERS) == 2

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Tender).where(Tender.tender_ref == "GEM/2023/B/3489664"))
            tender = result.scalar_one()
            assert tender.organization == "BHEL"
            assert tender.status == "unknown"
            # Dates/value were never verifiable (bhel.com is blocked from
            # this sandbox too) — must stay null, not guessed.
            assert tender.closing_date is None
            assert tender.estimated_value is None

            source_result = await db.execute(select(Source).where(Source.id == tender.source_id))
            source = source_result.scalar_one()
            assert source.url == "https://gem.gov.in/"
    finally:
        await _cleanup()


async def test_seed_gem_tenders_is_idempotent():
    await _cleanup()
    try:
        async with AsyncSessionLocal() as db:
            await seed_government_sources(db)
            await seed_gem_tenders(db)

        async with AsyncSessionLocal() as db:
            second_run = await seed_gem_tenders(db)
            assert second_run == 0
    finally:
        await _cleanup()


async def test_seed_gem_tenders_is_a_noop_without_the_source():
    await _cleanup()
    try:
        async with AsyncSessionLocal() as db:
            # Deliberately skip seed_government_sources() — the GeM source
            # doesn't exist yet, so this must return 0, not crash or
            # attempt to create tenders with no source_id.
            inserted = await seed_gem_tenders(db)
            assert inserted == 0
    finally:
        await _cleanup()
