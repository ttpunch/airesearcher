import uuid

import pytest
from sqlalchemy import delete

from app.agent.citations import extract_cited_chunk_ids, verify_citations
from app.core.db import AsyncSessionLocal
from app.core.embeddings import LocalHashEmbeddingProvider
from app.models.chunk import Chunk
from app.models.document import Document
from app.models.source import Source


def test_extract_cited_chunk_ids_dedupes_and_preserves_order():
    text = "BHEL manufactures turbines [chunk:5]. It also makes boilers [chunk:2] and [chunk:5] again."
    assert extract_cited_chunk_ids(text) == [5, 2]


def test_extract_cited_chunk_ids_no_citations():
    assert extract_cited_chunk_ids("I cannot verify this from public sources.") == []


def test_extract_cited_chunk_ids_ignores_malformed_markers():
    assert extract_cited_chunk_ids("See [chunk:abc] and [chunk] and [chunks:5]") == []


@pytest.fixture
async def real_chunk():
    async with AsyncSessionLocal() as db:
        source = Source(
            name="Citation test source", url=f"internal://citation-test-{uuid.uuid4()}", source_type="test", tier="T2"
        )
        db.add(source)
        await db.commit()
        await db.refresh(source)

        document = Document(
            source_id=source.id,
            url="https://example.org/doc",
            content_hash="citationtesthash",
            storage_path="test/citation",
            mime_type="text/plain",
            status="chunked",
            extracted_text="irrelevant",
        )
        db.add(document)
        await db.commit()
        await db.refresh(document)

        provider = LocalHashEmbeddingProvider()
        [embedding] = await provider.embed(["citable content"])
        chunk = Chunk(document_id=document.id, chunk_index=0, content="citable content", embedding=embedding)
        db.add(chunk)
        await db.commit()
        await db.refresh(chunk)

        yield db, chunk, source, document

        await db.execute(delete(Chunk).where(Chunk.document_id == document.id))
        await db.execute(delete(Document).where(Document.id == document.id))
        await db.execute(delete(Source).where(Source.id == source.id))
        await db.commit()


async def test_verify_citations_accepts_a_grounded_real_chunk(real_chunk):
    db, chunk, source, document = real_chunk

    verified, unverifiable = await verify_citations(db, [chunk.id], retrieved_chunk_ids={chunk.id})

    assert unverifiable == []
    [v] = verified
    assert v.chunk_id == chunk.id
    assert v.content == "citable content"
    assert v.source_name == source.name
    assert v.source_tier == "T2"
    assert v.document_id == document.id


async def test_verify_citations_rejects_real_chunk_not_retrieved_this_turn(real_chunk):
    """The core anti-hallucination guarantee: a chunk_id that genuinely
    exists in the DB is still rejected if the model didn't actually see it
    via a tool call this turn — otherwise the model could cite any chunk_id
    it guesses or recalls from a previous conversation.
    """
    db, chunk, _source, _document = real_chunk

    verified, unverifiable = await verify_citations(db, [chunk.id], retrieved_chunk_ids=set())

    assert verified == []
    assert unverifiable == [chunk.id]


async def test_verify_citations_rejects_nonexistent_chunk_id(real_chunk):
    db, _chunk, _source, _document = real_chunk
    fake_id = 999_999_999

    verified, unverifiable = await verify_citations(db, [fake_id], retrieved_chunk_ids={fake_id})

    assert verified == []
    assert unverifiable == [fake_id]


async def test_verify_citations_empty_input():
    async with AsyncSessionLocal() as db:
        verified, unverifiable = await verify_citations(db, [], retrieved_chunk_ids=set())
        assert verified == []
        assert unverifiable == []
