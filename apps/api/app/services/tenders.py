"""Bid-pattern aggregation over the Tender table.

Deliberately just real SQL aggregation of whatever tenders are actually in
the database — this is not a "competitive bid-pattern analysis" AI feature
faking insight over data we don't have. Public tender award/bid outcomes
are rarely published in structured form, so v1's honest scope is: group
what's known (organization, status) and count it, rather than inventing a
win-rate or competitor-bid model this system has no evidence for.
"""

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crawler.hwr_tenders import LIST_URL, SOURCE_NAME, fetch_live_tenders
from app.models.source import Source
from app.models.tender import Tender
from app.schemas.tender import OrganizationBidStats, TenderAnalysis


async def analyze_tenders(db: AsyncSession) -> TenderAnalysis:
    result = await db.execute(select(Tender))
    tenders = list(result.scalars().all())

    by_status: Counter[str] = Counter()
    by_org_status: dict[str, Counter[str]] = defaultdict(Counter)

    for tender in tenders:
        by_status[tender.status] += 1
        by_org_status[tender.organization][tender.status] += 1

    by_organization = [
        OrganizationBidStats(organization=org, total=sum(counts.values()), by_status=dict(counts))
        for org, counts in sorted(by_org_status.items())
    ]

    return TenderAnalysis(
        total_tenders=len(tenders),
        by_status=dict(by_status),
        by_organization=by_organization,
    )


HWR_ORGANIZATION = "BHEL Haridwar"

# Fields a re-sync may legitimately need to refresh — a corrigendum can
# move the closing date, or amend the description, after the tender was
# first seen.
_REFRESHABLE_FIELDS = ("title", "closing_date", "estimated_value", "published_date", "url")


@dataclass
class HwrSyncResult:
    source_created: bool
    total_fetched: int
    tenders_created: int
    tenders_updated: int


async def _get_or_create_hwr_source(db: AsyncSession) -> tuple[Source, bool]:
    result = await db.execute(select(Source).where(Source.url == LIST_URL))
    source = result.scalar_one_or_none()
    if source is not None:
        return source, False
    source = Source(name=SOURCE_NAME, url=LIST_URL, source_type="tender_portal", tier="T1")
    db.add(source)
    await db.flush()
    return source, True


async def sync_hwr_tenders(db: AsyncSession, client: httpx.AsyncClient) -> HwrSyncResult:
    """Fetches BHEL Haridwar's live tender list and upserts it into the
    Tender table, idempotent by tender_ref (falls back to NIT serial —
    see app/crawler/hwr_tenders.py). All 126+ live tenders come from one
    HTTP request; see that module's docstring for why no per-tender
    fetch is needed.
    """
    source, source_created = await _get_or_create_hwr_source(db)
    source.last_crawled_at = datetime.now(UTC)

    fetched = await fetch_live_tenders(client)
    created = updated = 0

    for row in fetched:
        result = await db.execute(select(Tender).where(Tender.tender_ref == row.tender_ref))
        existing = result.scalar_one_or_none()
        new_values = {
            "title": row.title,
            "closing_date": row.closing_date,
            "estimated_value": row.estimated_value,
            "published_date": row.published_date,
            "url": row.url,
        }
        if existing is None:
            db.add(
                Tender(
                    source_id=source.id,
                    tender_ref=row.tender_ref,
                    organization=HWR_ORGANIZATION,
                    status="open",
                    **new_values,
                )
            )
            created += 1
            continue

        changed = any(getattr(existing, field) != value for field, value in new_values.items())
        if changed:
            for field in _REFRESHABLE_FIELDS:
                setattr(existing, field, new_values[field])
            updated += 1

    await db.commit()
    return HwrSyncResult(
        source_created=source_created,
        total_fetched=len(fetched),
        tenders_created=created,
        tenders_updated=updated,
    )
