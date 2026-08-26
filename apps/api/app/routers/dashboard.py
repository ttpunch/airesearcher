from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.chunk import Chunk
from app.models.document import Document
from app.models.entity import Entity
from app.models.opportunity import Opportunity
from app.models.research_report import ResearchReport
from app.models.source import Source
from app.models.tender import Tender
from app.schemas.dashboard import DashboardCounts, DashboardSummary

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


async def _count(db: AsyncSession, model) -> int:
    result = await db.execute(select(func.count()).select_from(model))
    return result.scalar_one()


@router.get("/summary", response_model=DashboardSummary)
async def get_summary(db: AsyncSession = Depends(get_db)) -> DashboardSummary:
    counts = DashboardCounts(
        sources=await _count(db, Source),
        documents=await _count(db, Document),
        chunks=await _count(db, Chunk),
        tenders=await _count(db, Tender),
        entities=await _count(db, Entity),
        research_reports=await _count(db, ResearchReport),
        opportunities=await _count(db, Opportunity),
    )

    top_result = await db.execute(select(Opportunity).order_by(Opportunity.weighted_score.desc()).limit(5))
    top_opportunities = list(top_result.scalars().all())

    return DashboardSummary(counts=counts, top_opportunities=top_opportunities)
