from pydantic import BaseModel

from app.schemas.opportunity import OpportunityRead


class DashboardCounts(BaseModel):
    sources: int
    documents: int
    chunks: int
    tenders: int
    entities: int
    research_reports: int
    opportunities: int


class DashboardSummary(BaseModel):
    counts: DashboardCounts
    top_opportunities: list[OpportunityRead]
