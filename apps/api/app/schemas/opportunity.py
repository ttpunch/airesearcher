from datetime import datetime

from pydantic import BaseModel, ConfigDict


class OpportunityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    feasibility: str
    strategic_value: str
    weighted_score: int
    tech_summary: str
    timeline: str
    risk: str
    source_section: str
    status: str
    approved_by: str | None
    approved_at: datetime | None
    created_at: datetime


class ApprovalRequest(BaseModel):
    approved_by: str
