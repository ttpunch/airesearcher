"""Fetch a Source's URL, store the raw content, and record a Document.

Deliberately synchronous/on-demand for Week 2 — no task queue yet. A
crawl is triggered per-source (via the API endpoint added in the next
step) rather than on a schedule; scheduling is a later concern, added
only once there's a real need for it.
"""

import hashlib
from datetime import UTC, datetime

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import storage
from app.crawler.robots import USER_AGENT, can_fetch
from app.models.document import Document
from app.models.source import Source


class RobotsDisallowed(Exception):
    pass


async def crawl_source(db: AsyncSession, source: Source, client: httpx.AsyncClient) -> Document:
    if not await can_fetch(client, source.url):
        raise RobotsDisallowed(f"robots.txt disallows fetching {source.url}")

    response = await client.get(source.url, headers={"User-Agent": USER_AGENT}, timeout=20.0, follow_redirects=True)
    response.raise_for_status()

    content = response.content
    content_hash = hashlib.sha256(content).hexdigest()
    content_type = response.headers.get("content-type", "application/octet-stream").split(";")[0]

    key = f"sources/{source.id}/{content_hash}"
    await storage.put_object(key, content, content_type)

    document = Document(
        source_id=source.id,
        url=str(response.url),
        content_hash=content_hash,
        storage_path=key,
        mime_type=content_type,
        status="fetched",
    )
    db.add(document)

    source.last_crawled_at = datetime.now(UTC)

    await db.commit()
    await db.refresh(document)
    return document
