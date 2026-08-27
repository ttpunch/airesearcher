import uuid

import pytest
from sqlalchemy import delete, select

from app.core.config import settings
from app.core.db import AsyncSessionLocal
from app.core.embeddings import LocalHashEmbeddingProvider
from app.models.chunk import Chunk
from app.models.document import Document
from app.models.source import Source
from app.processing.pipeline import NoExtractableText, process_document


@pytest.fixture
async def sample_document():
    async with AsyncSessionLocal() as db:
        # Unique per run: if a previous run's cleanup didn't complete (e.g.
        # an assertion failure aborts the fixture's teardown), a fixed URL
        # here would collide with leftover data on the next run instead of
        # failing cleanly.
        unique_url = f"internal://pipeline-test-{uuid.uuid4()}"
        source = Source(name="Pipeline test source", url=unique_url, source_type="test", tier="T1")
        db.add(source)
        await db.commit()
        await db.refresh(source)

        document = Document(
            source_id=source.id,
            url=None,
            content_hash="pipelinehash",
            storage_path="test/pipeline",
            mime_type="text/plain",
            status="extracted",
            extracted_text="\n\n".join(f"Paragraph {i} about BHEL turbines and boilers." for i in range(30)),
        )
        db.add(document)
        await db.commit()
        await db.refresh(document)

        yield db, document

        await db.execute(delete(Chunk).where(Chunk.document_id == document.id))
        await db.execute(delete(Document).where(Document.id == document.id))
        await db.execute(delete(Source).where(Source.id == source.id))
        await db.commit()


async def test_process_document_creates_chunks_with_embeddings(sample_document):
    db, document = sample_document
    provider = LocalHashEmbeddingProvider()

    chunks = await process_document(db, document, provider)

    assert len(chunks) > 0
    for i, chunk in enumerate(chunks):
        assert chunk.chunk_index == i
        assert chunk.document_id == document.id
        assert len(chunk.embedding) == settings.embedding_dim
        assert chunk.content in document.extracted_text or chunk.content

    await db.refresh(document)
    assert document.status == "chunked"


async def test_process_document_is_idempotent_by_default(sample_document):
    db, document = sample_document
    provider = LocalHashEmbeddingProvider()

    first = await process_document(db, document, provider)
    second = await process_document(db, document, provider)

    assert [c.id for c in first] == [c.id for c in second]

    result = await db.execute(select(Chunk).where(Chunk.document_id == document.id))
    assert len(list(result.scalars().all())) == len(first)


async def test_process_document_force_recreates_chunks(sample_document):
    db, document = sample_document
    provider = LocalHashEmbeddingProvider()

    first = await process_document(db, document, provider)
    first_ids = {c.id for c in first}

    second = await process_document(db, document, provider, force=True)
    second_ids = {c.id for c in second}

    assert first_ids.isdisjoint(second_ids)
    assert len(first) == len(second)

    result = await db.execute(select(Chunk).where(Chunk.document_id == document.id))
    assert len(list(result.scalars().all())) == len(second)


async def test_process_document_raises_on_no_extracted_text(sample_document):
    db, document = sample_document
    document.extracted_text = None
    provider = LocalHashEmbeddingProvider()

    with pytest.raises(NoExtractableText):
        await process_document(db, document, provider)
