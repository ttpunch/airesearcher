from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SourceCreate(BaseModel):
    name: str
    url: str
    source_type: str
    tier: str


class SourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    url: str
    source_type: str
    tier: str
    active: bool
    last_crawled_at: datetime | None
    created_at: datetime
