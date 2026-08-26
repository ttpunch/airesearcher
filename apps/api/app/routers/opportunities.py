from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.opportunity import Opportunity
from app.schemas.opportunity import ApprovalRequest, OpportunityRead

router = APIRouter(prefix="/api/opportunities", tags=["opportunities"])


@router.get("", response_model=list[OpportunityRead])
async def list_opportunities(
    status: str | None = None, db: AsyncSession = Depends(get_db)
) -> list[Opportunity]:
    query = select(Opportunity).order_by(Opportunity.weighted_score.desc())
    if status is not None:
        query = query.where(Opportunity.status == status)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/{opportunity_id}", response_model=OpportunityRead)
async def get_opportunity(opportunity_id: int, db: AsyncSession = Depends(get_db)) -> Opportunity:
    opportunity = await db.get(Opportunity, opportunity_id)
    if opportunity is None:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return opportunity


async def _decide(
    opportunity_id: int, new_status: str, payload: ApprovalRequest, db: AsyncSession
) -> Opportunity:
    opportunity = await db.get(Opportunity, opportunity_id)
    if opportunity is None:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    if opportunity.status != "proposed":
        raise HTTPException(
            status_code=409, detail=f"Opportunity already {opportunity.status}, cannot re-decide"
        )
    if not payload.approved_by or not payload.approved_by.strip():
        raise HTTPException(status_code=400, detail="approved_by must not be empty")

    opportunity.status = new_status
    opportunity.approved_by = payload.approved_by
    opportunity.approved_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(opportunity)
    return opportunity


@router.post("/{opportunity_id}/approve", response_model=OpportunityRead)
async def approve_opportunity(
    opportunity_id: int, payload: ApprovalRequest, db: AsyncSession = Depends(get_db)
) -> Opportunity:
    """RECOMMENDATION-tagged output requires explicit human approval per
    AGENTS.md's hard constraint — there is no path that sets status to
    "approved" other than this endpoint being called by a human. Note:
    approved_by is a plain free-text field, not backed by real
    authentication — a known, documented gap for this project's current
    stage (see Opportunity's docstring and AGENTS.md).
    """
    return await _decide(opportunity_id, "approved", payload, db)


@router.post("/{opportunity_id}/reject", response_model=OpportunityRead)
async def reject_opportunity(
    opportunity_id: int, payload: ApprovalRequest, db: AsyncSession = Depends(get_db)
) -> Opportunity:
    return await _decide(opportunity_id, "rejected", payload, db)
