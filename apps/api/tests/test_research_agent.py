"""Tests the orchestration logic in app/agent/research_agent.py against a
scripted fake for claude_agent_sdk.query() — this sandbox has no
ANTHROPIC_API_KEY, and the user asked not to spend real API usage
verifying this here (see conversation). The fake never invokes the real
search tool (it isn't going through the actual SDK's tool-dispatch
machinery), so any [chunk:N] the fake's scripted answer cites is
correctly treated as ungrounded/unverifiable by this module's own logic —
that's real, meaningful behavior being tested, not a gap: it's the same
anti-hallucination path a real ungrounded citation would hit. The
grounded/happy-path citation flow (a real retrieved chunk_id getting
verified) is covered directly in test_agent_citations.py and
test_agent_tools.py against the real tool + real DB.
"""

from claude_agent_sdk import AssistantMessage, ResultMessage, TextBlock

from app.agent.research_agent import (
    SEARCH_TOOL_NAME,
    build_agent_options,
    run_research_query,
)
from app.core.db import AsyncSessionLocal
from app.core.embeddings import LocalHashEmbeddingProvider


async def _fake_query_single_assistant_message(*, prompt, options):
    yield AssistantMessage(
        content=[TextBlock(text=f"BHEL manufactures turbines [FACT] [chunk:404]. Question was: {prompt}")],
        model="claude-test",
    )


async def _fake_query_result_message_wins(*, prompt, options):
    yield AssistantMessage(content=[TextBlock(text="draft answer, ignored")], model="claude-test")
    yield ResultMessage(
        subtype="success",
        duration_ms=10,
        duration_api_ms=10,
        is_error=False,
        num_turns=1,
        session_id="test-session",
        result="Final answer after tool use [chunk:404].",
    )


async def _fake_query_no_citations(*, prompt, options):
    yield AssistantMessage(
        content=[TextBlock(text="I cannot verify this from public sources.")], model="claude-test"
    )


async def test_run_research_query_uses_assistant_message_text():
    async with AsyncSessionLocal() as db:
        provider = LocalHashEmbeddingProvider()
        response = await run_research_query(db, "What does BHEL manufacture?", provider, query_fn=_fake_query_single_assistant_message)

        assert "BHEL manufactures turbines" in response.answer
        # chunk:404 was never retrieved via the real tool this turn, so it
        # must NOT come back as a verified citation.
        assert response.citations == []
        assert response.unverifiable_citation_count == 1


async def test_run_research_query_prefers_result_message_over_draft_text():
    async with AsyncSessionLocal() as db:
        provider = LocalHashEmbeddingProvider()
        response = await run_research_query(db, "question", provider, query_fn=_fake_query_result_message_wins)

        assert response.answer == "Final answer after tool use [chunk:404]."
        assert "draft answer" not in response.answer


async def test_run_research_query_handles_no_citations_gracefully():
    async with AsyncSessionLocal() as db:
        provider = LocalHashEmbeddingProvider()
        response = await run_research_query(db, "question with no answer", provider, query_fn=_fake_query_no_citations)

        assert response.answer == "I cannot verify this from public sources."
        assert response.citations == []
        assert response.unverifiable_citation_count == 0


async def test_build_agent_options_wires_the_search_tool_and_evidence_rules():
    async with AsyncSessionLocal() as db:
        provider = LocalHashEmbeddingProvider()
        options = build_agent_options(db, provider, retrieved_chunk_ids=set())

        assert options.allowed_tools == [f"mcp__bhel_research__{SEARCH_TOOL_NAME}"]
        assert "bhel_research" in options.mcp_servers
        assert "[chunk:<id>]" in options.system_prompt
        assert "I cannot verify this from public sources" in options.system_prompt
        assert options.permission_mode == "bypassPermissions"


async def test_run_research_query_uses_openai_compatible_loop_when_provider_is_not_anthropic(monkeypatch):
    """query_fn=None + a non-"anthropic" provider must route through
    app.agent.openai_compatible.run_tool_calling_loop, never through the
    real claude_agent_sdk.query() — stubbed here (not hitting real network,
    same "mock-verified only" discipline as the query_fn tests above) to
    prove the branch itself is wired correctly.
    """
    from app.agent import research_agent

    captured: dict = {}

    async def _fake_run_tool_calling_loop(config, system_prompt, user_prompt, tools, **kwargs):
        captured["config"] = config
        captured["tools"] = tools
        return "Answer from an OpenAI-compatible model [chunk:404]."

    monkeypatch.setattr(research_agent, "run_tool_calling_loop", _fake_run_tool_calling_loop)
    monkeypatch.setattr(research_agent.settings, "llm_provider", "deepseek")
    monkeypatch.setattr(research_agent.settings, "deepseek_api_key", "test-key")
    monkeypatch.setattr(research_agent.settings, "deepseek_model", "deepseek-chat")

    async with AsyncSessionLocal() as db:
        provider = LocalHashEmbeddingProvider()
        response = await run_research_query(db, "What does BHEL manufacture?", provider, query_fn=None)

        assert "Answer from an OpenAI-compatible model" in response.answer
        # chunk:404 was never actually retrieved via the (stubbed-out) tool,
        # so it must still be rejected — the branch doesn't bypass citation
        # verification just because the model backend changed.
        assert response.citations == []
        assert response.unverifiable_citation_count == 1

    assert captured["config"].model == "deepseek-chat"
    assert len(captured["tools"]) == 1
