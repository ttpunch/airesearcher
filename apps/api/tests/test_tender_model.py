import uuid
from datetime import date

from sqlalchemy import delete, select

from app.core.db import AsyncSessionLocal
from app.models.source import Source
from app.models.tender import Tender


async def test_tender_stores_and_retrieves():
    async with AsyncSessionLocal() as db:
        source = Source(
            name="Tender test source",
            url=f"internal://tender-test-{uuid.uuid4()}",
            source_type="tender_portal",
            tier="T1",
        )
        db.add(source)
        await db.commit()
        await db.refresh(source)

        try:
            tender = Tender(
                source_id=source.id,
                title="Supply of Boiler Auxiliaries",
                tender_ref="BHEL/TND/2026/001",
                organization="BHEL",
                url="https://www.bhel.com/tenders/example",
                published_date=date(2026, 1, 1),
                closing_date=date(2026, 2, 1),
                estimated_value="INR 5,00,00,000",
                status="open",
            )
            db.add(tender)
            await db.commit()
            await db.refresh(tender)

            assert tender.id is not None
            assert tender.status == "open"
            assert tender.extracted_requirements is None

            result = await db.execute(select(Tender).where(Tender.source_id == source.id))
            fetched = result.scalar_one()
            assert fetched.title == "Supply of Boiler Auxiliaries"
            assert fetched.organization == "BHEL"
        finally:
            await db.execute(delete(Tender).where(Tender.source_id == source.id))
            await db.execute(delete(Source).where(Source.id == source.id))
            await db.commit()


async def test_tender_status_defaults_to_unknown():
    async with AsyncSessionLocal() as db:
        source = Source(
            name="Tender default status source",
            url=f"internal://tender-test-{uuid.uuid4()}",
            source_type="tender_portal",
            tier="T1",
        )
        db.add(source)
        await db.commit()
        await db.refresh(source)

        try:
            tender = Tender(
                source_id=source.id,
                title="Untitled tender",
                organization="BHEL",
                url="https://www.bhel.com/tenders/example2",
            )
            db.add(tender)
            await db.commit()
            await db.refresh(tender)

            assert tender.status == "unknown"
        finally:
            await db.execute(delete(Tender).where(Tender.source_id == source.id))
            await db.execute(delete(Source).where(Source.id == source.id))
            await db.commit()
