"""Seed the source registry with BHEL's known Tier-1 official URLs,
identified during this project's Phase 1 research (see
docs/research/bhel-ai-strategy.html §2). Idempotent — get-or-create by
url, same pattern as the upload source in app/routers/documents.py — so
it's safe to run on every app startup rather than as a one-off migration.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entity import Entity, Relationship
from app.models.opportunity import Opportunity
from app.models.source import Source
from app.models.tender import Tender

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


# The strategy report's Top 10 Strategic Initiatives (§10) and their
# weighted scores from the Business Value/ROI Framework (§23) —
# already-researched, already-sourced content from this project's own
# Phase 3-6 work, not newly invented here. `feasibility="A"` on every row
# reflects the report's own scoping decision that V1 builds public-data-only
# versions of all ten (see §26-27's public->internal evolution path per
# initiative) — an INFERENCE from that framing, not a literal per-item tag
# in the report (only Initiative 1 is explicitly tagged "(A/B)" there).
TOP_10_OPPORTUNITIES: list[dict] = [
    {
        "title": "BHEL Public Research Assistant (Q&A + evidence chain)",
        "description": "No unified way to ask \"what does BHEL publicly say/do about X\" across scattered official pages, filings, and EoIs. Extends to internal SharePoint/PLM once access is granted, same architecture.",
        "strategic_value": "Highest",
        "weighted_score": 13,
        "tech_summary": "Crawl + chunk + agentic retrieval + citation verification.",
        "timeline": "4-6wk",
        "risk": "Hallucination/citation accuracy, directly mitigated by the evidence system.",
        "source_section": "strategy-report-top-10-item-3",
    },
    {
        "title": "Tender Intelligence Platform",
        "description": "Tender response is manual; Phase 1 found BHEL and L&T split an NTPC bulk-tender bundle — a pattern nobody is systematically tracking. Discovery + requirement extraction + bid-pattern analysis + win-probability, unified.",
        "strategic_value": "High",
        "weighted_score": 12,
        "tech_summary": "Crawler + PDF extraction + agentic retrieval + classifier.",
        "timeline": "6-8wk core",
        "risk": "Portal fragility/rate-limits.",
        "source_section": "strategy-report-top-10-item-1",
    },
    {
        "title": "Competitive & Installed-Base Intelligence",
        "description": "Toshiba is selling AI monitoring directly onto NTPC's BHEL-built fleet; BHEL has no equivalent visibility layer of its own.",
        "strategic_value": "High",
        "weighted_score": 12,
        "tech_summary": "News crawl + entity extraction + registry DB.",
        "timeline": "6wk",
        "risk": "Attribution accuracy.",
        "source_section": "strategy-report-top-10-item-2",
    },
    {
        "title": "Maharatna Financial & Governance Dashboard",
        "description": "BHEL is on formal government notice over the Maharatna PAT criterion; no live public-facing tracker exists.",
        "strategic_value": "High",
        "weighted_score": 11,
        "tech_summary": "Structured filing extraction + threshold dashboard.",
        "timeline": "4-6wk",
        "risk": "Filing-format changes.",
        "source_section": "strategy-report-top-10-item-4",
    },
    {
        "title": "Customer Intelligence & Sales Signal Platform",
        "description": "Sales lacks systematic visibility into customer capex plans and which competitor technologies customers are adopting.",
        "strategic_value": "High",
        "weighted_score": 10,
        "tech_summary": "IR/news monitoring + entity linking.",
        "timeline": "3-4wk",
        "risk": "Noise/false positives.",
        "source_section": "strategy-report-top-10-item-6",
    },
    {
        "title": "Peer & Market Benchmarking Engine",
        "description": "No continuous view of BHEL vs. L&T / Siemens Energy / GE Vernova on financials and orders.",
        "strategic_value": "Medium-High",
        "weighted_score": 9,
        "tech_summary": "Structured competitor-filing extraction + comparison dashboard.",
        "timeline": "4wk",
        "risk": "Inconsistent competitor disclosure formats.",
        "source_section": "strategy-report-top-10-item-5",
    },
    {
        "title": "Supply Chain Risk & Import-Dependency Monitor",
        "description": "BHEL has a formal FY26 government target to cut import dependency 10% YoY, with no monitoring tool tracking it.",
        "strategic_value": "Medium-High",
        "weighted_score": 9,
        "tech_summary": "Supplier/trade-news monitoring + classification.",
        "timeline": "4-6wk",
        "risk": "Coverage gaps on niche components.",
        "source_section": "strategy-report-top-10-item-7",
    },
    {
        "title": "Emerging-Market Opportunity Radar (hydrogen / BESS / SMR)",
        "description": "BHEL is already moving into hydrogen and storage (the Hystar and thyssenkrupp nucera partnerships found in Phase 1) but has no systematic way to spot the next MNRE/CEA opening.",
        "strategic_value": "Medium-High",
        "weighted_score": 9,
        "tech_summary": "Policy monitoring + opportunity-scoring agent.",
        "timeline": "4-6wk",
        "risk": "False positives on early-stage policy signals.",
        "source_section": "strategy-report-top-10-item-8",
    },
    {
        "title": "Regulatory & Grid Intelligence Tracker",
        "description": "BHEL's business is regulated across six-plus ministries/bodies (Heavy Industries, Power, CEA, CERC, MNRE, Railways, Defence) with no single tracking view.",
        "strategic_value": "Medium-High",
        "weighted_score": 8,
        "tech_summary": "Multi-source monitoring + classification.",
        "timeline": "4-6wk",
        "risk": "Source fragmentation.",
        "source_section": "strategy-report-top-10-item-10",
    },
    {
        "title": "OT/Cybersecurity Threat Intelligence Monitor",
        "description": "BHEL's DCS/OT footprint is a real target; no dedicated public-advisory monitoring was found for it.",
        "strategic_value": "Medium-High",
        "weighted_score": 8,
        "tech_summary": "CERT-In/ICS-CERT feed monitoring, filtered to BHEL's known OT footprint.",
        "timeline": "4-6wk",
        "risk": "False negatives where BHEL's OT footprint isn't itself public.",
        "source_section": "strategy-report-top-10-item-9",
    },
]


async def seed_opportunities(db: AsyncSession) -> int:
    """Returns the number of new opportunities inserted. Idempotent by
    title (same pattern as the source/entity seeders).
    """
    inserted = 0
    for entry in TOP_10_OPPORTUNITIES:
        result = await db.execute(select(Opportunity).where(Opportunity.title == entry["title"]))
        if result.scalar_one_or_none() is not None:
            continue
        db.add(Opportunity(feasibility="A", status="proposed", **entry))
        inserted += 1
    if inserted:
        await db.commit()
    return inserted


# GeM (Government e-Marketplace, gem.gov.in) is India's central government
# procurement portal — BHEL, as a Maharatna PSU, posts tenders there
# (confirmed via web search: real BHEL pages on bhel.com link out to real
# GeM bid numbers like GEM/2023/B/3489664, and bidplus.gem.gov.in hosts
# real BHEL bid documents). Both gem.gov.in and bidplus.gem.gov.in are
# blocked by this project's dev sandbox's own network egress proxy, so
# their content could not be directly fetched/verified here — only
# confirmed to be real via search-engine-indexed snippets, not by loading
# the pages. No automated crawler was built against GeM: its bid-search
# is a dynamic, session-based interface (not a static page a simple
# robots-respecting GET crawler can meaningfully scrape), and building
# scraping logic against a page structure never actually seen would
# violate this project's "verify, don't fabricate" discipline. The manual
# POST /api/tenders / PDF-upload path remains how more real GeM tenders
# get added.
GOVERNMENT_SEED_SOURCES: list[dict[str, str]] = [
    {
        "name": "GeM — Government e-Marketplace",
        "url": "https://gem.gov.in/",
        "source_type": "tender_portal",
        "tier": "T1",
    },
]


async def seed_government_sources(db: AsyncSession) -> int:
    """Returns the number of new sources inserted."""
    inserted = 0
    for entry in GOVERNMENT_SEED_SOURCES:
        result = await db.execute(select(Source).where(Source.url == entry["url"]))
        if result.scalar_one_or_none() is not None:
            continue
        db.add(Source(**entry))
        inserted += 1
    if inserted:
        await db.commit()
    return inserted


# Two real GeM bid numbers for BHEL, found via web search this session on
# BHEL's own site (not guessed): the title is the actual BHEL page title
# text, the tender_ref is the real GeM bid number, and the url is the real
# bhel.com announcement page. published_date/closing_date/estimated_value
# are deliberately left null — bhel.com itself is also blocked by this
# sandbox's egress proxy, so those specific fields were never verifiable
# here, and this project doesn't fill an unverified field with a guess.
GEM_SEED_TENDERS: list[dict[str, str]] = [
    {
        "title": "Custom Bid / open tender through GeM portal [GEM/2022/B/2650225]",
        "tender_ref": "GEM/2022/B/2650225",
        "organization": "BHEL",
        "url": "https://bhel.com/custom-bid-open-tender-through-gem-portal-gem2022b2650225",
    },
    {
        "title": "Open Tender through GeM Portal for Procurement of Check Valve, Gate Valve and Regulating Globe Valve [GEM/2023/B/3489664]",
        "tender_ref": "GEM/2023/B/3489664",
        "organization": "BHEL",
        "url": "https://www.bhel.com/open-tender-through-gem-portal-gem-bid-no-gem2023b3489664-procurement-check-valve-gate-valve-and",
    },
]


async def seed_gem_tenders(db: AsyncSession) -> int:
    """Assumes seed_government_sources() has already run (in this session
    or a prior one) — looks up the GeM source by url rather than
    re-creating it. Idempotent by tender_ref; returns the number inserted.
    """
    result = await db.execute(select(Source).where(Source.url == GOVERNMENT_SEED_SOURCES[0]["url"]))
    gem_source = result.scalar_one_or_none()
    if gem_source is None:
        return 0

    inserted = 0
    for entry in GEM_SEED_TENDERS:
        result = await db.execute(select(Tender).where(Tender.tender_ref == entry["tender_ref"]))
        if result.scalar_one_or_none() is not None:
            continue
        db.add(Tender(source_id=gem_source.id, status="unknown", **entry))
        inserted += 1
    if inserted:
        await db.commit()
    return inserted
