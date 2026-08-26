"""The BHEL research agent — Claude Agent SDK, agentic retrieval, per the
architecture decided in AGENTS.md (Claude Agent SDK over LangGraph;
agentic retrieval over single-shot RAG). This is Week 4's MVP: a single
orchestrating agent with one tool (search), not the full multi-source
9-step Deep Research workflow — that's Week 9-10, generalizing this same
loop across tender/competitor/market source classes.

The `query_fn` parameter exists so tests can substitute a scripted async
generator for claude_agent_sdk.query() — this project's dev sandbox has
no ANTHROPIC_API_KEY and the user asked not to spend real API usage
verifying this here, so the orchestration logic (tool wiring, citation
extraction, verification) is tested against that boundary while the
search tool itself runs for real against a real DB.
"""

from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    create_sdk_mcp_server,
)
from claude_agent_sdk import (
    query as sdk_query,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.citations import (
    VerifiedCitation,
    extract_cited_chunk_ids,
    verify_citations,
)
from app.agent.tools import SEARCH_TOOL_NAME, make_search_tool
from app.core.embeddings import EmbeddingProvider

SYSTEM_PROMPT = f"""You are the BHEL Public Research Assistant. You answer questions using ONLY
the search_bhel_documents tool — never your own background knowledge about BHEL, since that
knowledge cannot be sourced or verified.

Rules, no exceptions:
1. For every question, call the search tool at least once. Re-search with a different query if
   your first search doesn't cover part of the question.
2. Every factual claim must be immediately followed by a citation in the exact form [chunk:<id>],
   using only a chunk_id that appeared in a search tool result this turn. Never cite a chunk_id
   you have not seen in a tool result, and never invent one.
3. Label each claim FACT (directly stated by the source), INFERENCE (reasonably derived, say how),
   or RECOMMENDATION (your judgment) — inline, e.g. "[FACT]" or "[INFERENCE]" before the claim.
4. If the search results do not support an answer, say plainly: "I cannot verify this from public sources."
   Do not fill the gap with unsourced knowledge.
5. Keep the answer focused and well-scoped rather than exhaustive.

Tool name: mcp__bhel_research__{SEARCH_TOOL_NAME}
"""

QueryFn = Callable[..., AsyncIterator[object]]


@dataclass
class AskResponse:
    answer: str
    citations: list[VerifiedCitation]
    unverifiable_citation_count: int


def build_agent_options(db: AsyncSession, embedding_provider: EmbeddingProvider, retrieved_chunk_ids: set[int]):
    search_tool = make_search_tool(db, embedding_provider, retrieved_chunk_ids)
    server = create_sdk_mcp_server(name="bhel_research", tools=[search_tool])

    return ClaudeAgentOptions(
        mcp_servers={"bhel_research": server},
        allowed_tools=[f"mcp__bhel_research__{SEARCH_TOOL_NAME}"],
        system_prompt=SYSTEM_PROMPT,
        permission_mode="bypassPermissions",  # single read-only search tool, no side effects
        max_turns=6,
    )


async def run_research_query(
    db: AsyncSession,
    question: str,
    embedding_provider: EmbeddingProvider,
    query_fn: QueryFn | None = None,
) -> AskResponse:
    query_fn = query_fn or sdk_query
    retrieved_chunk_ids: set[int] = set()
    options = build_agent_options(db, embedding_provider, retrieved_chunk_ids)

    answer_text = ""
    async for message in query_fn(prompt=question, options=options):
        if isinstance(message, AssistantMessage):
            text_blocks = [block.text for block in message.content if isinstance(block, TextBlock)]
            if text_blocks:
                answer_text = "\n".join(text_blocks)
        elif isinstance(message, ResultMessage) and message.result:
            answer_text = message.result

    cited_ids = extract_cited_chunk_ids(answer_text)
    verified, unverifiable_ids = await verify_citations(db, cited_ids, retrieved_chunk_ids)

    return AskResponse(answer=answer_text, citations=verified, unverifiable_citation_count=len(unverifiable_ids))
