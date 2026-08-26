import httpx
import pytest
from sqlalchemy import delete

from app.core import storage
from app.core.db import AsyncSessionLocal
from app.crawler.crawl import RobotsDisallowed, crawl_source
from app.crawler.robots import can_fetch
from app.models.document import Document
from app.models.source import Source

ROBOTS_TXT = "User-agent: *\nDisallow: /private/\n"
PAGE_HTML = "<html><body><h1>BHEL</h1><p>Test page content.</p></body></html>"


def mock_handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/robots.txt":
        return httpx.Response(200, text=ROBOTS_TXT)
    if request.url.path == "/page.html":
        return httpx.Response(200, text=PAGE_HTML, headers={"content-type": "text/html"})
    return httpx.Response(404)


@pytest.fixture
def mock_client():
    return httpx.AsyncClient(transport=httpx.MockTransport(mock_handler), base_url="http://test.example")


async def test_can_fetch_respects_robots_txt(mock_client):
    async with mock_client as client:
        assert await can_fetch(client, "http://test.example/page.html") is True
        assert await can_fetch(client, "http://test.example/private/secret.html") is False


async def test_crawl_source_stores_document_and_object(mock_client, s3_env):
    async with AsyncSessionLocal() as db:
        source = Source(
            name="Test BHEL page",
            url="http://test.example/page.html",
            source_type="bhel_official",
            tier="T1",
        )
        db.add(source)
        await db.commit()
        await db.refresh(source)

        try:
            async with mock_client as client:
                document = await crawl_source(db, source, client)

            assert document.id is not None
            assert document.source_id == source.id
            assert document.mime_type == "text/html"
            assert document.storage_path == f"sources/{source.id}/{document.content_hash}"

            stored_bytes = await storage.get_object(document.storage_path)
            assert stored_bytes.decode() == PAGE_HTML

            assert source.last_crawled_at is not None
        finally:
            await db.execute(delete(Document).where(Document.source_id == source.id))
            await db.execute(delete(Source).where(Source.id == source.id))
            await db.commit()


async def test_crawl_source_raises_on_disallowed_path(s3_env):
    disallowed_client = httpx.AsyncClient(transport=httpx.MockTransport(mock_handler), base_url="http://test.example")
    async with AsyncSessionLocal() as db:
        source = Source(
            name="Disallowed page",
            url="http://test.example/private/secret.html",
            source_type="bhel_official",
            tier="T1",
        )
        db.add(source)
        await db.commit()
        await db.refresh(source)

        try:
            async with disallowed_client as client:
                with pytest.raises(RobotsDisallowed):
                    await crawl_source(db, source, client)
        finally:
            await db.execute(delete(Source).where(Source.id == source.id))
            await db.commit()
