import uuid

import pytest
from sqlalchemy import delete

from app.core.db import AsyncSessionLocal
from app.core.embeddings import LocalHashEmbeddingProvider
from app.models.chunk import Chunk
from app.models.document import Document
from app.models.source import Source
from app.services.search import hybrid_search


@pytest.fixture
async def indexed_chunks():
    """Three chunks with deliberately distinct text, so pg_trgm similarity
    gives a real, checkable ranking signal independent of the (non-semantic)
    local embedding provider.

    hybrid_search intentionally searches the whole corpus, unscoped — that's
    correct product behavior, but it means other tests' data (including
    anything a previous run's incomplete cleanup left behind) can appear
    alongside this fixture's own results. Tests below use a generous limit
    and filter to `own_chunk_ids` before asserting on ranking/count, rather
    than assuming these 3 chunks are the only rows in the table.
    """
    async with AsyncSessionLocal() as db:
        source = Source(
            name="Search test source", url=f"internal://search-test-{uuid.uuid4()}", source_type="test", tier="T1"
        )
        db.add(source)
        await db.commit()
        await db.refresh(source)

        document = Document(
            source_id=source.id,
            url=None,
            content_hash="searchtesthash",
            storage_path="test/search",
            mime_type="text/plain",
            status="chunked",
            extracted_text="irrelevant for this fixture",
        )
        db.add(document)
        await db.commit()
        await db.refresh(document)

        provider = LocalHashEmbeddingProvider()
        texts = [
            "BHEL turbine manufacturing and steam generator production capacity.",
            "BHEL quarterly financial results and profit after tax figures.",
            "BHEL hydrogen electrolyser partnership with Hystar and thyssenkrupp nucera.",
        ]
        embeddings = await provider.embed(texts)
        chunks = [
            Chunk(document_id=document.id, chunk_index=i, content=text, embedding=embedding)
            for i, (text, embedding) in enumerate(zip(texts, embeddings, strict=True))
        ]
        db.add_all(chunks)
        await db.commit()
        for c in chunks:
            await db.refresh(c)

        yield db, texts, {c.id for c in chunks}

        await db.execute(delete(Chunk).where(Chunk.document_id == document.id))
        await db.execute(delete(Document).where(Document.id == document.id))
        await db.execute(delete(Source).where(Source.id == source.id))
        await db.commit()


async def test_hybrid_search_pure_text_ranks_matching_chunk_first(indexed_chunks):
    db, texts, own_chunk_ids = indexed_chunks
    provider = LocalHashEmbeddingProvider()

    results = await hybrid_search(db, "turbine manufacturing steam generator", provider, alpha=0.0, limit=100)
    own_results = [r for r in results if r.chunk.id in own_chunk_ids]

    assert len(own_results) == 3
    assert own_results[0].chunk.content == texts[0]
    assert own_results[0].text_score >= own_results[1].text_score >= own_results[2].text_score


async def test_hybrid_search_returns_real_distinct_vector_scores(indexed_chunks):
    db, _texts, own_chunk_ids = indexed_chunks
    provider = LocalHashEmbeddingProvider()

    results = await hybrid_search(db, "hydrogen electrolyser", provider, alpha=1.0, limit=100)
    own_results = [r for r in results if r.chunk.id in own_chunk_ids]

    assert len(own_results) == 3
    vector_scores = {r.vector_score for r in own_results}
    # Real cosine-distance computation against distinct real vectors — not
    # a stub that returns the same number for everything.
    assert len(vector_scores) == 3
    for score in vector_scores:
        assert -1.0 <= score <= 1.0


async def test_hybrid_search_respects_limit(indexed_chunks):
    db, _texts, _own_chunk_ids = indexed_chunks
    provider = LocalHashEmbeddingProvider()

    results = await hybrid_search(db, "BHEL", provider, limit=1)
    assert len(results) == 1


async def test_hybrid_search_includes_citation_data(indexed_chunks):
    db, _texts, own_chunk_ids = indexed_chunks
    provider = LocalHashEmbeddingProvider()

    results = await hybrid_search(db, "financial results", provider, alpha=0.0, limit=100)
    own_results = [r for r in results if r.chunk.id in own_chunk_ids]
    result = own_results[0]

    assert result.source.tier == "T1"
    assert result.document.id == result.chunk.document_id


async def test_hybrid_search_empty_query_returns_no_results(indexed_chunks):
    db, _texts, _own_chunk_ids = indexed_chunks
    provider = LocalHashEmbeddingProvider()

    assert await hybrid_search(db, "", provider) == []
    assert await hybrid_search(db, "   ", provider) == []


async def test_hybrid_search_rejects_invalid_alpha(indexed_chunks):
    db, _texts, _own_chunk_ids = indexed_chunks
    provider = LocalHashEmbeddingProvider()

    with pytest.raises(ValueError, match="alpha"):
        await hybrid_search(db, "some query", provider, alpha=1.5)
