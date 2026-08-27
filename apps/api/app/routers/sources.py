import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.crawler.crawl import RobotsDisallowed, crawl_source
from app.models.source import Source
from app.schemas.document import DocumentRead
from app.schemas.source import SourceCreate, SourceRead

router = APIRouter(prefix="/api/sources", tags=["sources"])


@router.get("", response_model=list[SourceRead])
async def list_sources(db: AsyncSession = Depends(get_db)) -> list[Source]:
    result = await db.execute(select(Source).order_by(Source.id))
    return list(result.scalars().all())


@router.post("", response_model=SourceRead, status_code=201)
async def create_source(payload: SourceCreate, db: AsyncSession = Depends(get_db)) -> Source:
    source = Source(**payload.model_dump())
    db.add(source)
    await db.commit()
    await db.refresh(source)
    return source


@router.post("/{source_id}/crawl", response_model=DocumentRead)
async def trigger_crawl(source_id: int, db: AsyncSession = Depends(get_db)):
    source = await db.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")

    async with httpx.AsyncClient() as client:
        try:
            return await crawl_source(db, source, client)
        except RobotsDisallowed as e:
            raise HTTPException(status_code=422, detail=str(e)) from e
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"Fetch failed: {e}") from e
