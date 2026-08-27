"""Deep Research workflow — Week 9-10's generalization of Week 4's
single-tool Ask loop (app/agent/research_agent.py) across all of BHEL's
source classes: indexed documents, tenders, and knowledge-graph entities
(competitors/technologies). Same Claude Agent SDK / agentic-retrieval
architecture (AGENTS.md), same evidence discipline, just three tools
instead of one and a topic-level report instead of a single answer.

Kept as a separate module from research_agent.py rather than merged into
it — Week 4's Ask endpoint and its tests stay untouched; this is an
additive generalization, not a replacement.

Same "mock-verified only" boundary as Week 4: query_fn is injectable so
tests never invoke the real claude_agent_sdk.query() (see
research_agent.py's module docstring for the full rationale).

Same provider branching as research_agent.py too: when query_fn is unset
and settings.llm_provider is "openrouter"/"deepseek" instead of the
default "anthropic", this runs all three tools through
app/agent/openai_compatible.py's hand-rolled tool-calling loop instead of
the Claude Agent SDK. Every caller that matters for tests still passes
query_fn explicitly, so that path is unaffected.
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

from app.agent.deep_research_tools import (
    SEARCH_ENTITIES_TOOL_NAME,
    SEARCH_TENDERS_TOOL_NAME,
    make_search_entities_tool,
    make_search_tenders_tool,
)
from app.agent.multi_citations import (
    VerifiedReference,
    extract_cited_references,
    verify_references,
)
from app.agent.openai_compatible import (
    get_openai_compatible_config,
    run_tool_calling_loop,
)
from app.agent.tools import SEARCH_TOOL_NAME, make_search_tool
from app.core.config import settings
from app.core.embeddings import EmbeddingProvider

SYSTEM_PROMPT = f"""You are the BHEL Deep Research Assistant. Given a research topic, you produce a
well-sourced report by searching across ALL of BHEL's indexed source classes — not just documents.

You have three tools:
- mcp__bhel_deep_research__{SEARCH_TOOL_NAME}: indexed documents (crawled + uploaded), cite with [chunk:<id>]
- mcp__bhel_deep_research__{SEARCH_TENDERS_TOOL_NAME}: registered tenders, cite with [tender:<id>]
- mcp__bhel_deep_research__{SEARCH_ENTITIES_TOOL_NAME}: BHEL/competitor/technology entities, cite with [entity:<id>]

Rules, no exceptions:
1. Use at least two different tools before writing the report, unless the topic is clearly scoped
   to only one source class. Re-search with a different query if a tool's first result is thin.
2. Every factual claim must be immediately followed by a citation in one of the exact forms above,
   using only an id that appeared in a tool result this turn. Never cite an id you have not seen in
   a tool result, and never invent one.
3. Label each claim FACT (directly stated by the source), INFERENCE (reasonably derived, say how),
   or RECOMMENDATION (your judgment) — inline, e.g. "[FACT]" or "[INFERENCE]" before the claim.
4. If nothing in any tool's results supports the topic, say plainly: "I cannot verify this from public sources."
   Do not fill the gap with unsourced knowledge.
5. Structure the report with short sections/headings rather than one undifferentiated block.
"""

QueryFn = Callable[..., AsyncIterator[object]]


@dataclass
class DeepResearchResult:
    summary: str
    references: list[VerifiedReference]
    unverifiable_reference_count: int


def build_deep_research_options(
    db: AsyncSession,
    embedding_provider: EmbeddingProvider,
    retrieved_ids_by_type: dict[str, set[int]],
):
    document_tool = make_search_tool(db, embedding_provider, retrieved_ids_by_type["chunk"])
    tenders_tool = make_search_tenders_tool(db, retrieved_ids_by_type["tender"])
    entities_tool = make_search_entities_tool(db, retrieved_ids_by_type["entity"])
    server = create_sdk_mcp_server(
        name="bhel_deep_research", tools=[document_tool, tenders_tool, entities_tool]
    )

    return ClaudeAgentOptions(
        mcp_servers={"bhel_deep_research": server},
        allowed_tools=[
            f"mcp__bhel_deep_research__{SEARCH_TOOL_NAME}",
            f"mcp__bhel_deep_research__{SEARCH_TENDERS_TOOL_NAME}",
            f"mcp__bhel_deep_research__{SEARCH_ENTITIES_TOOL_NAME}",
        ],
        system_prompt=SYSTEM_PROMPT,
        permission_mode="bypassPermissions",  # three read-only search tools, no side effects
        max_turns=10,
    )


async def run_deep_research(
    db: AsyncSession,
    topic: str,
    embedding_provider: EmbeddingProvider,
    query_fn: QueryFn | None = None,
) -> DeepResearchResult:
    retrieved_ids_by_type: dict[str, set[int]] = {"chunk": set(), "tender": set(), "entity": set()}

    if query_fn is not None or settings.llm_provider == "anthropic":
        query_fn = query_fn or sdk_query
        options = build_deep_research_options(db, embedding_provider, retrieved_ids_by_type)

        summary_text = ""
        async for message in query_fn(prompt=topic, options=options):
            if isinstance(message, AssistantMessage):
                text_blocks = [block.text for block in message.content if isinstance(block, TextBlock)]
                if text_blocks:
                    summary_text = "\n".join(text_blocks)
            elif isinstance(message, ResultMessage) and message.result:
                summary_text = message.result
    else:
        document_tool = make_search_tool(db, embedding_provider, retrieved_ids_by_type["chunk"])
        tenders_tool = make_search_tenders_tool(db, retrieved_ids_by_type["tender"])
        entities_tool = make_search_entities_tool(db, retrieved_ids_by_type["entity"])
        config = get_openai_compatible_config()
        summary_text = await run_tool_calling_loop(
            config, SYSTEM_PROMPT, topic, tools=[document_tool, tenders_tool, entities_tool]
        )

    cited_references = extract_cited_references(summary_text)
    verified, unverifiable = await verify_references(db, cited_references, retrieved_ids_by_type)

    return DeepResearchResult(
        summary=summary_text,
        references=verified,
        unverifiable_reference_count=len(unverifiable),
    )
