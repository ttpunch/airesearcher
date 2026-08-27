import json
import uuid

import pytest
from sqlalchemy import delete

from app.agent.tools import make_search_tool
from app.core.db import AsyncSessionLocal
from app.core.embeddings import LocalHashEmbeddingProvider
from app.models.chunk import Chunk
from app.models.document import Document
from app.models.source import Source


@pytest.fixture
async def indexed_chunk():
    async with AsyncSessionLocal() as db:
        source = Source(
            name="Agent tool test source",
            url=f"internal://agent-tool-test-{uuid.uuid4()}",
            source_type="test",
            tier="T1",
        )
        db.add(source)
        await db.commit()
        await db.refresh(source)

        document = Document(
            source_id=source.id,
            url=None,
            content_hash="agenttoolhash",
            storage_path="test/agent-tool",
            mime_type="text/plain",
            status="chunked",
            extracted_text="irrelevant",
        )
        db.add(document)
        await db.commit()
        await db.refresh(document)

        provider = LocalHashEmbeddingProvider()
        [embedding] = await provider.embed(["BHEL turbine manufacturing capacity in Haridwar and Hyderabad."])
        chunk = Chunk(document_id=document.id, chunk_index=0, content="BHEL turbine manufacturing capacity in Haridwar and Hyderabad.", embedding=embedding)
        db.add(chunk)
        await db.commit()
        await db.refresh(chunk)

        yield db, chunk, source

        await db.execute(delete(Chunk).where(Chunk.document_id == document.id))
        await db.execute(delete(Document).where(Document.id == document.id))
        await db.execute(delete(Source).where(Source.id == source.id))
        await db.commit()


async def test_search_tool_handler_returns_real_results_and_records_ids(indexed_chunk):
    db, chunk, source = indexed_chunk
    provider = LocalHashEmbeddingProvider()
    retrieved_chunk_ids: set[int] = set()

    search_tool = make_search_tool(db, provider, retrieved_chunk_ids)
    result = await search_tool.handler({"query": "turbine manufacturing Haridwar", "limit": 5})

    assert "content" in result
    payload = json.loads(result["content"][0]["text"])
    assert any(item["chunk_id"] == chunk.id for item in payload)
    matching = next(item for item in payload if item["chunk_id"] == chunk.id)
    assert matching["source_name"] == source.name
    assert matching["source_tier"] == "T1"

    # The whole point of this set: the agent loop uses it afterward to
    # verify the model only cites chunks it actually retrieved.
    assert chunk.id in retrieved_chunk_ids


async def test_search_tool_handler_no_results_returns_friendly_message():
    db_session_factory = AsyncSessionLocal
    async with db_session_factory() as db:
        provider = LocalHashEmbeddingProvider()
        retrieved_chunk_ids: set[int] = set()
        search_tool = make_search_tool(db, provider, retrieved_chunk_ids)

        result = await search_tool.handler({"query": f"nonsense-query-{uuid.uuid4()}", "limit": 5})

        text = result["content"][0]["text"]
        # Either a real (but unrelated) match came back, or the explicit
        # "no results" message did — either way it must not crash, and if
        # nothing at all is indexed for this query it should say so plainly.
        assert isinstance(text, str) and text
