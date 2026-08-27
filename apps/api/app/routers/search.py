from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.embeddings import EmbeddingProvider, get_embedding_provider
from app.schemas.search import CitationRead, SearchResultRead
from app.services.search import DEFAULT_ALPHA, hybrid_search

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("", response_model=list[SearchResultRead])
async def search(
    q: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=100),
    alpha: float = Query(DEFAULT_ALPHA, ge=0.0, le=1.0),
    db: AsyncSession = Depends(get_db),
    embedding_provider: EmbeddingProvider = Depends(get_embedding_provider),
) -> list[SearchResultRead]:
    try:
        results = await hybrid_search(db, q, embedding_provider, limit=limit, alpha=alpha)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return [
        SearchResultRead(
            chunk_id=r.chunk.id,
            chunk_index=r.chunk.chunk_index,
            content=r.chunk.content,
            vector_score=r.vector_score,
            text_score=r.text_score,
            hybrid_score=r.hybrid_score,
            citation=CitationRead(
                source_id=r.source.id,
                source_name=r.source.name,
                source_url=r.source.url,
                source_tier=r.source.tier,
                document_id=r.document.id,
                document_url=r.document.url,
            ),
        )
        for r in results
    ]
