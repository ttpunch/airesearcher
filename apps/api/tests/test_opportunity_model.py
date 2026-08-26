import uuid

from sqlalchemy import delete, select

from app.core.db import AsyncSessionLocal
from app.models.opportunity import Opportunity


async def test_opportunity_stores_and_retrieves_with_proposed_default():
    async with AsyncSessionLocal() as db:
        title = f"Test Opportunity {uuid.uuid4()}"
        opportunity = Opportunity(
            title=title,
            description="A test opportunity.",
            feasibility="A",
            strategic_value="High",
            weighted_score=10,
            tech_summary="Test tech.",
            timeline="4wk",
            risk="Test risk.",
            source_section="test",
        )
        db.add(opportunity)
        await db.commit()
        await db.refresh(opportunity)

        try:
            assert opportunity.id is not None
            assert opportunity.status == "proposed"
            assert opportunity.approved_by is None
            assert opportunity.approved_at is None

            result = await db.execute(select(Opportunity).where(Opportunity.title == title))
            fetched = result.scalar_one()
            assert fetched.weighted_score == 10
        finally:
            await db.execute(delete(Opportunity).where(Opportunity.id == opportunity.id))
            await db.commit()
