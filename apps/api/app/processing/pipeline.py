"""Chunk a Document's extracted text, embed each chunk, and store Chunk rows.

Idempotent by default: if the document already has chunks, returns them
unchanged rather than re-embedding (mainly to avoid burning API calls on
accidental re-processing). Pass force=True to delete and recreate.
"""

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.embeddings import EmbeddingProvider
from app.models.chunk import Chunk
from app.models.document import Document
from app.processing.chunking import chunk_text


class NoExtractableText(Exception):
    pass


async def process_document(
    db: AsyncSession,
    document: Document,
    embedding_provider: EmbeddingProvider,
    force: bool = False,
) -> list[Chunk]:
    if not force:
        existing = await db.execute(select(Chunk).where(Chunk.document_id == document.id).order_by(Chunk.chunk_index))
        existing_chunks = list(existing.scalars().all())
        if existing_chunks:
            return existing_chunks

    if not document.extracted_text or not document.extracted_text.strip():
        raise NoExtractableText(f"Document {document.id} has no extracted text to chunk")

    texts = chunk_text(document.extracted_text)
    if not texts:
        raise NoExtractableText(f"Document {document.id} produced zero chunks from its extracted text")

    embeddings = await embedding_provider.embed(texts)

    if force:
        await db.execute(delete(Chunk).where(Chunk.document_id == document.id))

    chunks = [
        Chunk(document_id=document.id, chunk_index=i, content=text, embedding=embedding)
        for i, (text, embedding) in enumerate(zip(texts, embeddings, strict=True))
    ]
    db.add_all(chunks)
    document.status = "chunked"
    await db.commit()
    for chunk in chunks:
        await db.refresh(chunk)
    return chunks
