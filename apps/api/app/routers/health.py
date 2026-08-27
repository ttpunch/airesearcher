from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.schemas.health import HealthResponse, StatusResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Static liveness check — no DB dependency, so it can't be blocked by a DB outage."""
    return HealthResponse(status="ok")


@router.get("/api/status", response_model=StatusResponse)
async def status(db: AsyncSession = Depends(get_db)) -> StatusResponse:
    """Full-stack connectivity check — proves the API can reach Postgres."""
    try:
        await db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:  # noqa: BLE001 — any DB failure here should degrade to "error", not 500
        db_status = "error"
    return StatusResponse(api="ok", db=db_status, timestamp=datetime.now(UTC).isoformat())
