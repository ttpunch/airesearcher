"""In-process SDK tool wrapping hybrid_search for the research agent.

Each request gets its own tool instance (via make_search_tool) so the
`retrieved_chunk_ids` set is per-request state, not a shared global — the
citation verifier in app/agent/citations.py uses it to reject any citation
the agent didn't actually retrieve through this tool this turn.
"""

import json

from claude_agent_sdk import SdkMcpTool, tool
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.embeddings import EmbeddingProvider
from app.services.search import hybrid_search

SEARCH_TOOL_NAME = "search_bhel_documents"


def make_search_tool(
    db: AsyncSession, embedding_provider: EmbeddingProvider, retrieved_chunk_ids: set[int]
) -> SdkMcpTool[dict]:
    @tool(
        SEARCH_TOOL_NAME,
        "Search BHEL's indexed public documents (crawled and user-uploaded) for passages "
        "relevant to a query. Returns ranked passages with a chunk_id for each — cite "
        "claims using that chunk_id, never a chunk_id you have not seen in a tool result.",
        {"query": str, "limit": int},
    )
    async def search_bhel_documents(args: dict) -> dict:
        query_text = args["query"]
        limit = int(args.get("limit") or 5)
        results = await hybrid_search(db, query_text, embedding_provider, limit=limit)

        for r in results:
            retrieved_chunk_ids.add(r.chunk.id)

        payload = [
            {
                "chunk_id": r.chunk.id,
                "content": r.chunk.content,
                "source_name": r.source.name,
                "source_tier": r.source.tier,
                "source_url": r.source.url,
            }
            for r in results
        ]
        if not payload:
            text = "No matching passages found for this query."
        else:
            text = json.dumps(payload, indent=2)
        return {"content": [{"type": "text", "text": text}]}

    return search_bhel_documents
