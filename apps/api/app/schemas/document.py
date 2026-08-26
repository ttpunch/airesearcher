from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_id: int
    url: str | None
    content_hash: str
    storage_path: str
    mime_type: str
    status: str
    fetched_at: datetime
