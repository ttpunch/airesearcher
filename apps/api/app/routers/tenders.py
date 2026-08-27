import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.crawler.crawl import RobotsDisallowed
from app.crawler.hwr_tenders import BASE_URL
from app.models.document import Document
from app.models.tender import Tender
from app.processing.tender_extraction import extract_tender_fields
from app.schemas.tender import (
    HwrSyncResultOut,
    TenderAnalysis,
    TenderCreate,
    TenderExtractResponse,
    TenderRead,
)
from app.services.tenders import analyze_tenders, sync_hwr_tenders

router = APIRouter(prefix="/api/tenders", tags=["tenders"])


def get_hwr_client() -> httpx.AsyncClient:
    """A seam for dependency-injection, same convention as
    app/routers/npp.py's get_npp_client: tests override this with a
    MockTransport-backed client so no test ever fetches hwr.bhel.com for
    real.
    """
    return httpx.AsyncClient(base_url=BASE_URL)


@router.get("", response_model=list[TenderRead])
async def list_tenders(
    status: str | None = None,
    organization: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[Tender]:
    query = select(Tender).order_by(Tender.id)
    if status is not None:
        query = query.where(Tender.status == status)
    if organization is not None:
        query = query.where(Tender.organization == organization)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/analyze", response_model=TenderAnalysis)
async def analyze(db: AsyncSession = Depends(get_db)) -> TenderAnalysis:
    return await analyze_tenders(db)


@router.post("/sync-hwr", response_model=HwrSyncResultOut)
async def sync_hwr(
    db: AsyncSession = Depends(get_db),
    client: httpx.AsyncClient = Depends(get_hwr_client),
) -> HwrSyncResultOut:
    """Live-fetches BHEL Haridwar's public online-tenders list
    (hwr.bhel.com) and upserts it into the Tender table — see
    app/crawler/hwr_tenders.py for what's actually fetched and why.
    Manual trigger, not run on startup, matching this project's stance on
    live network calls at boot (see app/routers/npp.py's sync endpoint
    for the same reasoning).
    """
    try:
        result = await sync_hwr_tenders(db, client)
    except RobotsDisallowed as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Fetch failed: {e}") from e

    return HwrSyncResultOut(
        source_created=result.source_created,
        total_fetched=result.total_fetched,
        tenders_created=result.tenders_created,
        tenders_updated=result.tenders_updated,
    )


@router.get("/{tender_id}", response_model=TenderRead)
async def get_tender(tender_id: int, db: AsyncSession = Depends(get_db)) -> Tender:
    tender = await db.get(Tender, tender_id)
    if tender is None:
        raise HTTPException(status_code=404, detail="Tender not found")
    return tender


@router.post("", response_model=TenderRead, status_code=201)
async def create_tender(payload: TenderCreate, db: AsyncSession = Depends(get_db)) -> Tender:
    tender = Tender(**payload.model_dump())
    db.add(tender)
    await db.commit()
    await db.refresh(tender)
    return tender


@router.post("/{tender_id}/extract", response_model=TenderExtractResponse)
async def extract_requirements(tender_id: int, db: AsyncSession = Depends(get_db)) -> TenderExtractResponse:
    tender = await db.get(Tender, tender_id)
    if tender is None:
        raise HTTPException(status_code=404, detail="Tender not found")
    if tender.document_id is None:
        raise HTTPException(status_code=422, detail="Tender has no linked document to extract from")

    document = await db.get(Document, tender.document_id)
    if document is None or not document.extracted_text:
        raise HTTPException(status_code=422, detail="Linked document has no extracted text")

    fields = extract_tender_fields(document.extracted_text)
    tender.extracted_requirements = fields.to_json()
    await db.commit()

    return TenderExtractResponse(
        tender_id=tender.id,
        closing_date_text=fields.closing_date_text,
        emd_amount_text=fields.emd_amount_text,
        tender_ref=fields.tender_ref,
        eligibility_snippets=fields.eligibility_snippets,
    )
