from sqlalchemy import delete, select

from app.core.db import AsyncSessionLocal
from app.core.seed import TOP_10_OPPORTUNITIES, seed_opportunities
from app.models.opportunity import Opportunity


async def _cleanup() -> None:
    async with AsyncSessionLocal() as db:
        titles = [o["title"] for o in TOP_10_OPPORTUNITIES]
        await db.execute(delete(Opportunity).where(Opportunity.title.in_(titles)))
        await db.commit()


async def test_seed_opportunities_creates_all_ten_as_proposed_feasibility_a():
    await _cleanup()
    try:
        async with AsyncSessionLocal() as db:
            first_run = await seed_opportunities(db)
            assert first_run == len(TOP_10_OPPORTUNITIES) == 10

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Opportunity))
            opportunities = result.scalars().all()
            assert len(opportunities) == 10
            assert all(o.status == "proposed" for o in opportunities)
            assert all(o.feasibility == "A" for o in opportunities)
            titles = {o.title for o in opportunities}
            assert "BHEL Public Research Assistant (Q&A + evidence chain)" in titles
    finally:
        await _cleanup()


async def test_seed_opportunities_is_idempotent():
    await _cleanup()
    try:
        async with AsyncSessionLocal() as db:
            await seed_opportunities(db)

        async with AsyncSessionLocal() as db:
            second_run = await seed_opportunities(db)
            assert second_run == 0
    finally:
        await _cleanup()
