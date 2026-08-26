import uuid

import pytest
from sqlalchemy import delete

from app.agent.multi_citations import extract_cited_references, verify_references
from app.core.db import AsyncSessionLocal
from app.core.embeddings import LocalHashEmbeddingProvider
from app.models.chunk import Chunk
from app.models.document import Document
from app.models.entity import Entity
from app.models.source import Source
from app.models.tender import Tender


def test_extract_cited_references_dedupes_and_preserves_order():
    text = "BHEL makes turbines [chunk:5]. See tender [tender:9] and competitor [entity:3], again [chunk:5]."
    assert extract_cited_references(text) == [("chunk", 5), ("tender", 9), ("entity", 3)]


def test_extract_cited_references_no_citations():
    assert extract_cited_references("I cannot verify this from public sources.") == []


def test_extract_cited_references_ignores_malformed_and_unknown_types():
    assert extract_cited_references("See [chunk:abc] and [document:5] and [chunk]") == []


@pytest.fixture
async def real_records():
    async with AsyncSessionLocal() as db:
        source = Source(
            name="Multi-citation test source",
            url=f"internal://multi-citation-test-{uuid.uuid4()}",
            source_type="test",
            tier="T1",
        )
        db.add(source)
        await db.commit()
        await db.refresh(source)

        document = Document(
            source_id=source.id,
            url=None,
            content_hash="multicitationhash",
            storage_path="test/multi-citation",
            mime_type="text/plain",
            status="chunked",
            extracted_text="irrelevant",
        )
        db.add(document)
        await db.commit()
        await db.refresh(document)

        provider = LocalHashEmbeddingProvider()
        [embedding] = await provider.embed(["citable content for multi-citation test"])
        chunk = Chunk(
            document_id=document.id, chunk_index=0, content="citable content for multi-citation test", embedding=embedding
        )
        db.add(chunk)

        tender = Tender(
            source_id=source.id,
            title="Multi-citation fixture tender",
            organization="BHEL",
            url="https://www.bhel.com/tenders/multi-citation-fixture",
            status="open",
        )
        db.add(tender)

        entity = Entity(name=f"Multi-citation fixture entity {uuid.uuid4()}", entity_type="technology")
        db.add(entity)

        await db.commit()
        await db.refresh(chunk)
        await db.refresh(tender)
        await db.refresh(entity)

        yield db, chunk, tender, entity, source

        await db.execute(delete(Chunk).where(Chunk.id == chunk.id))
        await db.execute(delete(Tender).where(Tender.id == tender.id))
        await db.execute(delete(Entity).where(Entity.id == entity.id))
        await db.execute(delete(Document).where(Document.id == document.id))
        await db.execute(delete(Source).where(Source.id == source.id))
        await db.commit()


async def test_verify_references_accepts_grounded_references_of_all_types(real_records):
    db, chunk, tender, entity, source = real_records
    cited = [("chunk", chunk.id), ("tender", tender.id), ("entity", entity.id)]
    retrieved = {"chunk": {chunk.id}, "tender": {tender.id}, "entity": {entity.id}}

    verified, unverifiable = await verify_references(db, cited, retrieved)

    assert unverifiable == []
    by_type = {(v.ref_type, v.ref_id): v for v in verified}
    assert by_type[("chunk", chunk.id)].label == source.name
    assert by_type[("tender", tender.id)].label == tender.title
    assert by_type[("entity", entity.id)].label == entity.name


async def test_verify_references_rejects_reference_not_retrieved_this_turn(real_records):
    db, chunk, tender, _entity, _source = real_records
    cited = [("chunk", chunk.id), ("tender", tender.id)]
    retrieved = {"chunk": set(), "tender": set(), "entity": set()}

    verified, unverifiable = await verify_references(db, cited, retrieved)

    assert verified == []
    assert set(unverifiable) == {("chunk", chunk.id), ("tender", tender.id)}


async def test_verify_references_rejects_nonexistent_ids():
    async with AsyncSessionLocal() as db:
        fake_id = 999_999_999
        cited = [("entity", fake_id)]
        retrieved = {"chunk": set(), "tender": set(), "entity": {fake_id}}

        verified, unverifiable = await verify_references(db, cited, retrieved)

        assert verified == []
        assert unverifiable == [("entity", fake_id)]


async def test_verify_references_empty_input():
    async with AsyncSessionLocal() as db:
        verified, unverifiable = await verify_references(db, [], {"chunk": set(), "tender": set(), "entity": set()})
        assert verified == []
        assert unverifiable == []
