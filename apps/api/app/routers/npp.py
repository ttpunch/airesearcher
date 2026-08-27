from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.models.entity import Entity
from app.models.source import Source
from app.portals.base import PortalError
from app.portals.npp.client import NppClient
from app.portals.npp.client import get_npp_client as _get_real_npp_client
from app.portals.npp.ingest import NPP_SOURCE_NAME, sync_npp
from app.portals.npp.models import NppCapacitySnapshot
from app.schemas.npp import NppStatusOut, NppSyncResultOut

router = APIRouter(prefix="/api/npp", tags=["npp"])


def get_npp_client() -> NppClient:
    """A seam for dependency-injection, same convention as
    app/routers/ask.py's get_ask_runner: tests override this with a
    MockTransport-backed client so no test ever fetches npp.gov.in for
    real.
    """
    return _get_real_npp_client()


@router.post("/sync", response_model=NppSyncResultOut)
async def sync(
    db: AsyncSession = Depends(get_db),
    client: NppClient = Depends(get_npp_client),
) -> NppSyncResultOut:
    if not settings.npp_enabled:
        raise HTTPException(status_code=503, detail="NPP integration is disabled (NPP_ENABLED=false)")

    try:
        result = await sync_npp(db, client)
    except PortalError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    return NppSyncResultOut(
        source_created=result.source_created,
        organizations_created=result.organizations_created,
        organizations_updated=result.organizations_updated,
        projects_created=result.projects_created,
        projects_updated=result.projects_updated,
        relationships_created=result.relationships_created,
        retrieved_at=result.retrieved_at,
    )


@router.get("/capacity-snapshot", response_model=NppCapacitySnapshot)
async def capacity_snapshot(client: NppClient = Depends(get_npp_client)) -> NppCapacitySnapshot:
    """A live pass-through to NPP's national capacity snapshot — not
    stored, not part of the KG sync. Cached in-process for
    settings.npp_cache_ttl_seconds (see app/portals/cache.py), so this is
    "real-time" in the sense of "fetched from NPP, not a manual sync
    snapshot," not millisecond-fresh; `reporting_date` vs `retrieved_at`
    in the response tells the caller both how current NPP's own figure is
    and when this process last actually fetched it.
    """
    if not settings.npp_enabled:
        raise HTTPException(status_code=503, detail="NPP integration is disabled (NPP_ENABLED=false)")
    try:
        return await client.capacity_snapshot()
    except PortalError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@router.get("/status", response_model=NppStatusOut)
async def status(db: AsyncSession = Depends(get_db)) -> NppStatusOut:
    source_result = await db.execute(select(Source).where(Source.name == NPP_SOURCE_NAME))
    source = source_result.scalar_one_or_none()

    async def _count(entity_type: str) -> int:
        result = await db.execute(select(func.count()).select_from(Entity).where(Entity.entity_type == entity_type))
        return result.scalar_one()

    return NppStatusOut(
        synced=source is not None,
        last_synced_at=source.last_crawled_at if source else None,
        power_organizations=await _count("power_organization"),
        power_projects=await _count("power_project"),
    )
