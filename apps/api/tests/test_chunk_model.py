from sqlalchemy import delete, select

from app.core.config import settings
from app.core.db import AsyncSessionLocal
from app.models.chunk import Chunk
from app.models.document import Document
from app.models.source import Source


async def test_chunk_stores_and_retrieves_real_vector():
    async with AsyncSessionLocal() as db:
        source = Source(name="Chunk test source", url="internal://chunk-test", source_type="test", tier="T1")
        db.add(source)
        await db.commit()
        await db.refresh(source)

        document = Document(
            source_id=source.id,
            url=None,
            content_hash="deadbeef",
            storage_path="test/path",
            mime_type="text/plain",
            status="extracted",
            extracted_text="hello world",
        )
        db.add(document)
        await db.commit()
        await db.refresh(document)

        try:
            embedding = [0.1] * settings.embedding_dim
            chunk = Chunk(document_id=document.id, chunk_index=0, content="hello world", embedding=embedding)
            db.add(chunk)
            await db.commit()
            await db.refresh(chunk)

            assert chunk.id is not None
            assert len(chunk.embedding) == settings.embedding_dim
            assert chunk.embedding[0] == 0.1

            result = await db.execute(select(Chunk).where(Chunk.document_id == document.id))
            fetched = result.scalar_one()
            assert fetched.content == "hello world"
        finally:
            await db.execute(delete(Chunk).where(Chunk.document_id == document.id))
            await db.execute(delete(Document).where(Document.id == document.id))
            await db.execute(delete(Source).where(Source.id == source.id))
            await db.commit()
