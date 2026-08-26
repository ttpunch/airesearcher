"""Additional in-process SDK tools for the Deep Research workflow
(app/agent/deep_research.py) — Week 9-10's generalization of Week 4's
single-tool Ask loop across BHEL's other source classes: tenders and KG
entities (competitors/technologies), alongside the existing document
search tool from app/agent/tools.py.

Same per-request-state pattern as make_search_tool: each tool records the
ids it actually returned into a shared set, so the citation verifier can
reject any [tender:<id>] or [entity:<id>] the agent didn't really retrieve
this turn.
"""

import json

from claude_agent_sdk import SdkMcpTool, tool
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entity import Entity
from app.models.source import Source
from app.models.tender import Tender

SEARCH_TENDERS_TOOL_NAME = "search_bhel_tenders"
SEARCH_ENTITIES_TOOL_NAME = "search_bhel_entities"


def make_search_tenders_tool(db: AsyncSession, retrieved_tender_ids: set[int]) -> SdkMcpTool[dict]:
    @tool(
        SEARCH_TENDERS_TOOL_NAME,
        "Search registered tenders by keyword (matches title or organization). Returns each "
        "matching tender's tender_id — cite claims about a specific tender using [tender:<id>], "
        "never an id you have not seen in a tool result.",
        {"query": str, "limit": int},
    )
    async def search_bhel_tenders(args: dict) -> dict:
        query_text = args["query"]
        limit = int(args.get("limit") or 5)
        like = f"%{query_text}%"
        result = await db.execute(
            select(Tender)
            .where(or_(Tender.title.ilike(like), Tender.organization.ilike(like)))
            .order_by(Tender.id)
            .limit(limit)
        )
        tenders = list(result.scalars().all())

        for t in tenders:
            retrieved_tender_ids.add(t.id)

        payload = [
            {
                "tender_id": t.id,
                "title": t.title,
                "organization": t.organization,
                "status": t.status,
                "closing_date": t.closing_date.isoformat() if t.closing_date else None,
                "url": t.url,
            }
            for t in tenders
        ]
        text = json.dumps(payload, indent=2) if payload else "No matching tenders found for this query."
        return {"content": [{"type": "text", "text": text}]}

    return search_bhel_tenders


def make_search_entities_tool(db: AsyncSession, retrieved_entity_ids: set[int]) -> SdkMcpTool[dict]:
    @tool(
        SEARCH_ENTITIES_TOOL_NAME,
        "Search knowledge-graph entities (BHEL, competitors, technologies) by keyword (matches "
        "name or description). Returns each matching entity's entity_id — cite claims about a "
        "specific entity using [entity:<id>], never an id you have not seen in a tool result.",
        {"query": str, "limit": int},
    )
    async def search_bhel_entities(args: dict) -> dict:
        query_text = args["query"]
        limit = int(args.get("limit") or 5)
        like = f"%{query_text}%"
        result = await db.execute(
            select(Entity, Source)
            .outerjoin(Source, Entity.source_id == Source.id)
            .where(or_(Entity.name.ilike(like), Entity.description.ilike(like)))
            .order_by(Entity.id)
            .limit(limit)
        )
        rows = result.all()

        for entity, _source in rows:
            retrieved_entity_ids.add(entity.id)

        payload = [
            {
                "entity_id": entity.id,
                "name": entity.name,
                "entity_type": entity.entity_type,
                "description": entity.description,
                "source_url": source.url if source else None,
            }
            for entity, source in rows
        ]
        text = json.dumps(payload, indent=2) if payload else "No matching entities found for this query."
        return {"content": [{"type": "text", "text": text}]}

    return search_bhel_entities
