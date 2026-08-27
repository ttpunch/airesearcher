from datetime import datetime

from pydantic import BaseModel


class ResearchRequest(BaseModel):
    topic: str


class ReferenceOut(BaseModel):
    ref_type: str
    ref_id: int
    label: str
    detail: str | None
    url: str | None
    tier: str | None


class ResearchReportOut(BaseModel):
    id: int
    topic: str
    summary: str
    references: list[ReferenceOut]
    unverifiable_reference_count: int
    status: str
    created_at: datetime
