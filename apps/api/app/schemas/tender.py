from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class TenderCreate(BaseModel):
    source_id: int
    document_id: int | None = None
    title: str
    tender_ref: str | None = None
    organization: str
    url: str
    published_date: date | None = None
    closing_date: date | None = None
    estimated_value: str | None = None
    status: str = "unknown"


class TenderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_id: int
    document_id: int | None
    title: str
    tender_ref: str | None
    organization: str
    url: str
    published_date: date | None
    closing_date: date | None
    estimated_value: str | None
    status: str
    extracted_requirements: str | None
    created_at: datetime


class TenderExtractResponse(BaseModel):
    tender_id: int
    closing_date_text: str | None
    emd_amount_text: str | None
    tender_ref: str | None
    eligibility_snippets: list[str]


class OrganizationBidStats(BaseModel):
    organization: str
    total: int
    by_status: dict[str, int]


class TenderAnalysis(BaseModel):
    total_tenders: int
    by_status: dict[str, int]
    by_organization: list[OrganizationBidStats]


class HwrSyncResultOut(BaseModel):
    source_created: bool
    total_fetched: int
    tenders_created: int
    tenders_updated: int
