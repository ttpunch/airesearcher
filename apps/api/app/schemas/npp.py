from datetime import datetime

from pydantic import BaseModel


class NppSyncResultOut(BaseModel):
    source_created: bool
    organizations_created: int
    organizations_updated: int
    projects_created: int
    projects_updated: int
    relationships_created: int
    retrieved_at: datetime


class NppStatusOut(BaseModel):
    synced: bool
    last_synced_at: datetime | None
    power_organizations: int
    power_projects: int
