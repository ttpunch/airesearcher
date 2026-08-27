"""Bid-pattern aggregation over the Tender table.

Deliberately just real SQL aggregation of whatever tenders are actually in
the database — this is not a "competitive bid-pattern analysis" AI feature
faking insight over data we don't have. Public tender award/bid outcomes
are rarely published in structured form, so v1's honest scope is: group
what's known (organization, status) and count it, rather than inventing a
win-rate or competitor-bid model this system has no evidence for.
"""

from collections import Counter, defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
