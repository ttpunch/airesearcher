"""Tests for app/services/tenders.py::sync_hwr_tenders against a real
local Postgres (same discipline as tests/test_npp_ingest.py) —
httpx.MockTransport stands in for hwr.bhel.com.
"""

import uuid
from pathlib import Path

import httpx
from sqlalchemy import delete, select

from app.core.db import AsyncSessionLocal
from app.crawler.hwr_tenders import SOURCE_NAME
from app.models.source import Source
from app.models.tender import Tender
from app.services.tenders import HWR_ORGANIZATION, sync_hwr_tenders

FIXTURE = (Path(__file__).parent / "fixtures" / "hwr_tenders" / "tenderlist.html").read_text(encoding="utf-8")


def _handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/robots.txt":
        return httpx.Response(404)
    if request.url.path == "/tenders/onlinetenders/tenderlist.jsp":
        return httpx.Response(200, text=FIXTURE)
    return httpx.Response(404)


def make_client() -> httpx.AsyncClient:
    base_url = f"https://hwr-test-{uuid.uuid4().hex}.example"
    return httpx.AsyncClient(transport=httpx.MockTransport(_handler), base_url=base_url)


async def _cleanup() -> None:
    async with AsyncSessionLocal() as db:
        await db.execute(delete(Tender).where(Tender.organization == HWR_ORGANIZATION))
        await db.execute(delete(Source).where(Source.name == SOURCE_NAME))
        await db.commit()


async def test_sync_creates_source_and_tenders():
    await _cleanup()
    try:
        async with AsyncSessionLocal() as db:
            result = await sync_hwr_tenders(db, make_client())
            assert result.source_created is True
            assert result.total_fetched == 3
            assert result.tenders_created == 3
            assert result.tenders_updated == 0

        async with AsyncSessionLocal() as db:
            source = (await db.execute(select(Source).where(Source.name == SOURCE_NAME))).scalar_one()
            assert source.source_type == "tender_portal"
            assert source.tier == "T1"
            assert source.last_crawled_at is not None

            tenders = (
                (await db.execute(select(Tender).where(Tender.organization == HWR_ORGANIZATION))).scalars().all()
            )
            assert len(tenders) == 3
            assert all(t.source_id == source.id for t in tenders)
    finally:
        await _cleanup()


async def test_sync_persists_real_fields():
    await _cleanup()
    try:
        async with AsyncSessionLocal() as db:
            await sync_hwr_tenders(db, make_client())

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Tender).where(Tender.tender_ref == "GEM/2026/B/7966022"))
            tender = result.scalar_one()
            assert tender.organization == HWR_ORGANIZATION
            assert tender.status == "open"
            assert tender.estimated_value == "14"
            assert tender.closing_date is not None
            assert tender.url.endswith("ten_no=19169")
    finally:
        await _cleanup()


async def test_sync_is_idempotent_on_unchanged_data():
    await _cleanup()
    try:
        async with AsyncSessionLocal() as db:
            await sync_hwr_tenders(db, make_client())

        async with AsyncSessionLocal() as db:
            second = await sync_hwr_tenders(db, make_client())
            assert second.source_created is False
            assert second.tenders_created == 0
            assert second.tenders_updated == 0
    finally:
        await _cleanup()


async def test_sync_updates_changed_closing_date_without_duplicating():
    await _cleanup()
    try:
        async with AsyncSessionLocal() as db:
            await sync_hwr_tenders(db, make_client())

        async with AsyncSessionLocal() as db:
            tender = (
                await db.execute(select(Tender).where(Tender.tender_ref == "GEM/2026/B/7966022"))
            ).scalar_one()
            tender.closing_date = None
            await db.commit()

        async with AsyncSessionLocal() as db:
            result = await sync_hwr_tenders(db, make_client())
            assert result.tenders_created == 0
            assert result.tenders_updated == 1

        async with AsyncSessionLocal() as db:
            all_tenders = (
                (await db.execute(select(Tender).where(Tender.organization == HWR_ORGANIZATION))).scalars().all()
            )
            assert len(all_tenders) == 3  # no duplicate row
            refreshed = next(t for t in all_tenders if t.tender_ref == "GEM/2026/B/7966022")
            assert refreshed.closing_date is not None
    finally:
        await _cleanup()
