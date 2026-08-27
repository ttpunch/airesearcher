"""Citation verification — the load-bearing piece of the evidence system
(strategy report §17). A citation is only shown as verified once we
confirm the agent actually retrieved that chunk through the search tool
this turn — not merely that a chunk with that id happens to exist, which
would let the model cite an id it invented or recalled from elsewhere.
"""

import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chunk import Chunk
from app.models.document import Document
from app.models.source import Source

CITATION_PATTERN = re.compile(r"\[chunk:(\d+)\]")


@dataclass
class VerifiedCitation:
    chunk_id: int
    content: str
    source_name: str
    source_url: str
    source_tier: str
    document_id: int


def extract_cited_chunk_ids(answer_text: str) -> list[int]:
    """Order-preserving, de-duplicated — first citation of each id wins."""
    seen: dict[int, None] = {}
    for match in CITATION_PATTERN.finditer(answer_text):
        seen.setdefault(int(match.group(1)), None)
    return list(seen.keys())


async def verify_citations(
    db: AsyncSession, cited_chunk_ids: list[int], retrieved_chunk_ids: set[int]
) -> tuple[list[VerifiedCitation], list[int]]:
    """Returns (verified citations, chunk_ids cited but not retrieved this
    turn — i.e. unverifiable, should never be presented as evidence).
    """
    grounded_ids = [cid for cid in cited_chunk_ids if cid in retrieved_chunk_ids]
    unverifiable_ids = [cid for cid in cited_chunk_ids if cid not in retrieved_chunk_ids]

    if not grounded_ids:
        return [], unverifiable_ids

    result = await db.execute(
        select(Chunk, Document, Source)
        .join(Document, Chunk.document_id == Document.id)
        .join(Source, Document.source_id == Source.id)
        .where(Chunk.id.in_(grounded_ids))
    )
    rows = {chunk.id: (chunk, document, source) for chunk, document, source in result.all()}

    verified: list[VerifiedCitation] = []
    for chunk_id in grounded_ids:
        row = rows.get(chunk_id)
        if row is None:
            # Retrieved this turn but gone from the DB by the time we verify
            # (deleted mid-request) — treat as unverifiable rather than crash.
            unverifiable_ids.append(chunk_id)
            continue
        chunk, document, source = row
        verified.append(
            VerifiedCitation(
                chunk_id=chunk.id,
                content=chunk.content,
                source_name=source.name,
                source_url=source.url,
                source_tier=source.tier,
                document_id=document.id,
            )
        )
    return verified, unverifiable_ids
