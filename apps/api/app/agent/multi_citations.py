"""Generalized citation verification for the Deep Research workflow —
same anti-hallucination discipline as app/agent/citations.py (a reference
is only verified if it was both retrieved via a real tool call this turn
AND still exists in the DB), extended to three reference types instead of
just chunks: [chunk:<id>], [tender:<id>], [entity:<id>].

Kept as a separate module rather than modifying app/agent/citations.py so
Week 4's Ask loop (and its tests) stay untouched — this generalizes the
pattern for Deep Research without risking a regression in the MVP path.
"""

import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chunk import Chunk
from app.models.document import Document
from app.models.entity import Entity
from app.models.source import Source
from app.models.tender import Tender

REFERENCE_PATTERN = re.compile(r"\[(chunk|tender|entity):(\d+)\]")


@dataclass
class VerifiedReference:
    ref_type: str
    ref_id: int
    label: str
    detail: str | None
    url: str | None
    tier: str | None


def extract_cited_references(answer_text: str) -> list[tuple[str, int]]:
    """Order-preserving, de-duplicated — first citation of each (type, id) wins."""
    seen: dict[tuple[str, int], None] = {}
    for match in REFERENCE_PATTERN.finditer(answer_text):
        seen.setdefault((match.group(1), int(match.group(2))), None)
    return list(seen.keys())


async def _verify_chunks(db: AsyncSession, ids: list[int]) -> dict[int, VerifiedReference]:
    if not ids:
        return {}
    result = await db.execute(
        select(Chunk, Document, Source)
        .join(Document, Chunk.document_id == Document.id)
        .join(Source, Document.source_id == Source.id)
        .where(Chunk.id.in_(ids))
    )
    return {
        chunk.id: VerifiedReference(
            ref_type="chunk",
            ref_id=chunk.id,
            label=source.name,
            detail=chunk.content,
            url=source.url,
            tier=source.tier,
        )
        for chunk, document, source in result.all()
    }


async def _verify_tenders(db: AsyncSession, ids: list[int]) -> dict[int, VerifiedReference]:
    if not ids:
        return {}
    result = await db.execute(select(Tender).where(Tender.id.in_(ids)))
    return {
        tender.id: VerifiedReference(
            ref_type="tender",
            ref_id=tender.id,
            label=tender.title,
            detail=f"{tender.organization} — {tender.status}",
            url=tender.url,
            tier=None,
        )
        for tender in result.scalars().all()
    }


async def _verify_entities(db: AsyncSession, ids: list[int]) -> dict[int, VerifiedReference]:
    if not ids:
        return {}
    result = await db.execute(
        select(Entity, Source).outerjoin(Source, Entity.source_id == Source.id).where(Entity.id.in_(ids))
    )
    return {
        entity.id: VerifiedReference(
            ref_type="entity",
            ref_id=entity.id,
            label=entity.name,
            detail=entity.description,
            url=source.url if source else None,
            tier=None,
        )
        for entity, source in result.all()
    }


_VERIFIERS = {"chunk": _verify_chunks, "tender": _verify_tenders, "entity": _verify_entities}


async def verify_references(
    db: AsyncSession,
    cited_references: list[tuple[str, int]],
    retrieved_ids_by_type: dict[str, set[int]],
) -> tuple[list[VerifiedReference], list[tuple[str, int]]]:
    """Returns (verified references in citation order, unverifiable (type, id)
    pairs — cited but not retrieved this turn, or retrieved but gone from
    the DB by verification time).
    """
    grounded: list[tuple[str, int]] = []
    unverifiable: list[tuple[str, int]] = []
    for ref_type, ref_id in cited_references:
        if ref_id in retrieved_ids_by_type.get(ref_type, set()):
            grounded.append((ref_type, ref_id))
        else:
            unverifiable.append((ref_type, ref_id))

    ids_by_type: dict[str, list[int]] = {"chunk": [], "tender": [], "entity": []}
    for ref_type, ref_id in grounded:
        ids_by_type[ref_type].append(ref_id)

    rows_by_type = {
        ref_type: await verifier(db, ids_by_type[ref_type]) for ref_type, verifier in _VERIFIERS.items()
    }

    verified: list[VerifiedReference] = []
    for ref_type, ref_id in grounded:
        row = rows_by_type[ref_type].get(ref_id)
        if row is None:
            unverifiable.append((ref_type, ref_id))
            continue
        verified.append(row)

    return verified, unverifiable
