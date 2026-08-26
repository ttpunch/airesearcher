import hashlib

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import storage
from app.core.db import get_db
from app.models.document import Document
from app.models.source import Source
from app.processing.pdf import PdfExtractionError, extract_text
from app.schemas.document import DocumentRead

router = APIRouter(prefix="/api/documents", tags=["documents"])

UPLOAD_SOURCE_NAME = "User Upload"
UPLOAD_SOURCE_URL = "internal://user-upload"


@router.get("", response_model=list[DocumentRead])
async def list_documents(source_id: int | None = None, db: AsyncSession = Depends(get_db)) -> list[Document]:
    query = select(Document).order_by(Document.id)
    if source_id is not None:
        query = query.where(Document.source_id == source_id)
    result = await db.execute(query)
    return list(result.scalars().all())


async def _get_or_create_upload_source(db: AsyncSession) -> Source:
    """Every manually-uploaded document is attributed to this one synthetic
    Source, tiered "UP" (user-provided, not yet cross-verified) per the
    evidence system design in the strategy report's §17.
    """
    result = await db.execute(select(Source).where(Source.url == UPLOAD_SOURCE_URL))
    source = result.scalar_one_or_none()
    if source is not None:
        return source

    source = Source(name=UPLOAD_SOURCE_NAME, url=UPLOAD_SOURCE_URL, source_type="user_upload", tier="UP")
    db.add(source)
    await db.commit()
    await db.refresh(source)
    return source


@router.post("/upload", response_model=DocumentRead, status_code=201)
async def upload_document(file: UploadFile, db: AsyncSession = Depends(get_db)) -> Document:
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only application/pdf uploads are supported for now")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    try:
        extracted_text = await extract_text(content)
    except PdfExtractionError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    source = await _get_or_create_upload_source(db)

    content_hash = hashlib.sha256(content).hexdigest()
    key = f"sources/{source.id}/{content_hash}"
    await storage.put_object(key, content, file.content_type)

    document = Document(
        source_id=source.id,
        url=None,
        content_hash=content_hash,
        storage_path=key,
        mime_type=file.content_type,
        status="extracted" if extracted_text else "needs_ocr",
        extracted_text=extracted_text or None,
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)
    return document
