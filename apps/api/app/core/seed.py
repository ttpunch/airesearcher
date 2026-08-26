"""Seed the source registry with BHEL's known Tier-1 official URLs,
identified during this project's Phase 1 research (see
docs/research/bhel-ai-strategy.html §2). Idempotent — get-or-create by
url, same pattern as the upload source in app/routers/documents.py — so
it's safe to run on every app startup rather than as a one-off migration.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entity import Entity, Relationship
from app.models.source import Source

BHEL_SEED_SOURCES: list[dict[str, str]] = [
    {
        "name": "BHEL — Home",
        "url": "https://www.bhel.com/",
        "source_type": "bhel_official",
        "tier": "T1",
    },
    {
        "name": "BHEL — Product & Services",
        "url": "https://www.bhel.com/product-services",
        "source_type": "bhel_official",
        "tier": "T1",
    },
    {
        "name": "BHEL — Research & Development",
        "url": "https://www.bhel.com/research-development",
        "source_type": "bhel_official",
        "tier": "T1",
    },
    {
        "name": "BHEL — Centres of Excellence",
        "url": "https://www.bhel.com/bhels-centres-excellence",
        "source_type": "bhel_official",
        "tier": "T1",
    },
    {
        "name": "BHEL — Tenders",
        "url": "https://www.bhel.com/tenders",
        "source_type": "tender_portal",
        "tier": "T1",
    },
]


async def seed_sources(db: AsyncSession) -> int:
    """Returns the number of new sources inserted."""
    inserted = 0
    for entry in BHEL_SEED_SOURCES:
        result = await db.execute(select(Source).where(Source.url == entry["url"]))
        if result.scalar_one_or_none() is not None:
            continue
        db.add(Source(**entry))
        inserted += 1
    if inserted:
        await db.commit()
    return inserted


# Domains verified live via web search during this project's Week 7 work
# (not guessed) — see AGENTS.md's Week 7 note. Scoped to the handful of
# competitors the strategy report's Phase 1 competitive-landscape research
# names as the closest overlap with BHEL's power-equipment segment.
COMPETITOR_SEED_SOURCES: list[dict[str, str]] = [
    {
        "name": "L&T Power",
        "url": "https://www.lntpower.com/",
        "source_type": "competitor",
        "tier": "T1",
    },
    {
        "name": "Siemens Energy",
        "url": "https://www.siemens-energy.com/global/en/home.html",
        "source_type": "competitor",
        "tier": "T1",
    },
    {
        "name": "GE Vernova",
        "url": "https://www.gevernova.com/",
        "source_type": "competitor",
        "tier": "T1",
    },
    {
        "name": "Thermax",
        "url": "https://www.thermaxglobal.com/",
        "source_type": "competitor",
        "tier": "T1",
    },
]


async def seed_competitor_sources(db: AsyncSession) -> int:
    """Returns the number of new sources inserted."""
    inserted = 0
    for entry in COMPETITOR_SEED_SOURCES:
        result = await db.execute(select(Source).where(Source.url == entry["url"]))
        if result.scalar_one_or_none() is not None:
            continue
        db.add(Source(**entry))
        inserted += 1
    if inserted:
        await db.commit()
    return inserted


# Technology concepts named in the strategy report's Phase 2 AI-landscape
# research (docs/research/bhel-ai-strategy.html §4-5) — these are KG nodes,
# not crawlable sources, so they carry no source_id.
TECHNOLOGY_ENTITIES: list[dict[str, str]] = [
    {"name": "Digital Twin", "description": "Virtual replica of a physical asset/process, updated from real data."},
    {"name": "Agentic AI", "description": "AI systems that plan, use tools, and act toward a goal with limited supervision."},
    {"name": "GraphRAG", "description": "Retrieval-augmented generation that traverses a knowledge graph, not just vector search."},
    {"name": "IIoT", "description": "Industrial Internet of Things — networked sensors/actuators on industrial equipment."},
]


async def _get_or_create_entity(
    db: AsyncSession, name: str, entity_type: str, description: str | None, source_id: int | None
) -> tuple[Entity, bool]:
    result = await db.execute(select(Entity).where(Entity.name == name, Entity.entity_type == entity_type))
    entity = result.scalar_one_or_none()
    if entity is not None:
        return entity, False
    entity = Entity(name=name, entity_type=entity_type, description=description, source_id=source_id)
    db.add(entity)
    await db.flush()
    return entity, True


async def _get_or_create_relationship(
    db: AsyncSession, from_entity_id: int, to_entity_id: int, relation_type: str, description: str | None
) -> bool:
    result = await db.execute(
        select(Relationship).where(
            Relationship.from_entity_id == from_entity_id,
            Relationship.to_entity_id == to_entity_id,
            Relationship.relation_type == relation_type,
        )
    )
    if result.scalar_one_or_none() is not None:
        return False
    db.add(
        Relationship(
            from_entity_id=from_entity_id,
            to_entity_id=to_entity_id,
            relation_type=relation_type,
            description=description,
        )
    )
    return True


async def seed_entities(db: AsyncSession) -> int:
    """Seeds BHEL, the seeded competitors, and named technology concepts as
    KG entities, plus a handful of relationships connecting them. Assumes
    seed_sources() and seed_competitor_sources() have already run in this
    session (or a prior one) — competitor entities are linked to their
    Source row by looking it up by URL, not by re-creating it. Idempotent
    like the source seeders; returns the number of new rows (entities +
    relationships) inserted.
    """
    inserted = 0

    async def _source_id_for_url(url: str) -> int | None:
        result = await db.execute(select(Source).where(Source.url == url))
        source = result.scalar_one_or_none()
        return source.id if source is not None else None

    bhel_source_id = await _source_id_for_url(BHEL_SEED_SOURCES[0]["url"])
    bhel_entity, created = await _get_or_create_entity(
        db, "BHEL", "organization", "Bharat Heavy Electricals Limited — Indian state-owned heavy engineering PSU.", bhel_source_id
    )
    inserted += int(created)

    competitor_entities: list[Entity] = []
    for src in COMPETITOR_SEED_SOURCES:
        source_id = await _source_id_for_url(src["url"])
        entity, created = await _get_or_create_entity(db, src["name"], "competitor", None, source_id)
        competitor_entities.append(entity)
        inserted += int(created)

    technology_entities: list[Entity] = []
    for tech in TECHNOLOGY_ENTITIES:
        entity, created = await _get_or_create_entity(db, tech["name"], "technology", tech["description"], None)
        technology_entities.append(entity)
        inserted += int(created)

    for competitor in competitor_entities:
        created = await _get_or_create_relationship(
            db, bhel_entity.id, competitor.id, "competes_with", "Overlaps with BHEL's power/industrial equipment segments."
        )
        inserted += int(created)

    for technology in technology_entities:
        created = await _get_or_create_relationship(
            db, technology.id, bhel_entity.id, "relevant_to", "Named as a relevant technology direction in the strategy report."
        )
        inserted += int(created)

    if inserted:
        await db.commit()
    return inserted
