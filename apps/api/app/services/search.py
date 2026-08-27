"""Hybrid search: pgvector cosine similarity + pg_trgm text similarity,
combined into one ranked result — the retrieval half of the evidence
system described in the strategy report's §17. A search result without
its source (name, url, tier) isn't useful for a citation-driven product,
so this returns the full join rather than bare chunks.
"""

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.embeddings import EmbeddingProvider
from app.models.chunk import Chunk
from app.models.document import Document
from app.models.source import Source

DEFAULT_ALPHA = 0.5  # weight on vector similarity vs. text similarity


@dataclass
class SearchResult:
    chunk: Chunk
    document: Document
    source: Source
    vector_score: float
    text_score: float
    hybrid_score: float


async def hybrid_search(
    db: AsyncSession,
    query_text: str,
    embedding_provider: EmbeddingProvider,
    limit: int = 10,
    alpha: float = DEFAULT_ALPHA,
) -> list[SearchResult]:
    if not query_text or not query_text.strip():
        return []
    if not 0.0 <= alpha <= 1.0:
        raise ValueError("alpha must be between 0.0 and 1.0")

    [query_embedding] = await embedding_provider.embed([query_text])

    vector_score_expr = 1 - Chunk.embedding.cosine_distance(query_embedding)
    text_score_expr = func.similarity(Chunk.content, query_text)
    hybrid_score_expr = alpha * vector_score_expr + (1 - alpha) * text_score_expr

    stmt = (
        select(
            Chunk,
            Document,
            Source,
            vector_score_expr.label("vector_score"),
            text_score_expr.label("text_score"),
            hybrid_score_expr.label("hybrid_score"),
        )
        .join(Document, Chunk.document_id == Document.id)
        .join(Source, Document.source_id == Source.id)
        .order_by(hybrid_score_expr.desc())
        .limit(limit)
    )

    result = await db.execute(stmt)
    return [
        SearchResult(
            chunk=chunk,
            document=document,
            source=source,
            vector_score=vector_score,
            text_score=text_score,
            hybrid_score=hybrid_score,
        )
        for chunk, document, source, vector_score, text_score, hybrid_score in result.all()
    ]
