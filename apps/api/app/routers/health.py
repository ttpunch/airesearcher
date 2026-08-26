from fastapi import APIRouter

from app.schemas.health import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Static liveness check — no DB dependency, so it can't be blocked by a DB outage."""
    return HealthResponse(status="ok")
