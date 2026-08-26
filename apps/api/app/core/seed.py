"""Seed the source registry with BHEL's known Tier-1 official URLs,
identified during this project's Phase 1 research (see
docs/research/bhel-ai-strategy.html §2). Idempotent — get-or-create by
url, same pattern as the upload source in app/routers/documents.py — so
it's safe to run on every app startup rather than as a one-off migration.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.source import Source

BHEL_SEED_SOURCES: list[dict[str, str]] = [
    {
        "name": "BHEL — Home",
        "url": "https://www.bhel.com/",
        "source_type": "bhel_official",
        "tier": "T1",
    },
    {
        "name": "BHEL — Product & Services",
        "url": "https://www.bhel.com/product-services",
        "source_type": "bhel_official",
        "tier": "T1",
    },
    {
        "name": "BHEL — Research & Development",
        "url": "https://www.bhel.com/research-development",
        "source_type": "bhel_official",
        "tier": "T1",
    },
    {
        "name": "BHEL — Centres of Excellence",
        "url": "https://www.bhel.com/bhels-centres-excellence",
        "source_type": "bhel_official",
        "tier": "T1",
    },
]


async def seed_sources(db: AsyncSession) -> int:
    """Returns the number of new sources inserted."""
    inserted = 0
    for entry in BHEL_SEED_SOURCES:
        result = await db.execute(select(Source).where(Source.url == entry["url"]))
        if result.scalar_one_or_none() is not None:
            continue
        db.add(Source(**entry))
        inserted += 1
    if inserted:
        await db.commit()
    return inserted
