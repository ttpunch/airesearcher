from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str


class StatusResponse(BaseModel):
    api: str
    db: str
    timestamp: str
