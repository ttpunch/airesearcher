"""Tests the orchestration logic in app/agent/deep_research.py against a
scripted fake for claude_agent_sdk.query() — same rationale as
test_research_agent.py: no real SDK call in this sandbox, "mock-verified
only" per the user's explicit choice. The grounded/happy-path citation
flow is covered directly in test_multi_citations.py and
test_deep_research_tools.py against the real tools + real DB.
"""

from claude_agent_sdk import AssistantMessage, ResultMessage, TextBlock

from app.agent.deep_research import (
    SEARCH_ENTITIES_TOOL_NAME,
    SEARCH_TENDERS_TOOL_NAME,
    SEARCH_TOOL_NAME,
    build_deep_research_options,
    run_deep_research,
)
from app.core.db import AsyncSessionLocal
from app.core.embeddings import LocalHashEmbeddingProvider


async def _fake_query_ungrounded_multi_type_citations(*, prompt, options):
    yield AssistantMessage(
        content=[
            TextBlock(
                text=(
                    f"BHEL manufactures turbines [FACT] [chunk:404]. A related tender is open "
                    f"[FACT] [tender:12]. Siemens Energy is a competitor [FACT] [entity:7]. Topic: {prompt}"
                )
            )
        ],
        model="claude-test",
    )


async def _fake_query_result_message_wins(*, prompt, options):
    yield AssistantMessage(content=[TextBlock(text="draft, ignored")], model="claude-test")
    yield ResultMessage(
        subtype="success",
        duration_ms=10,
        duration_api_ms=10,
        is_error=False,
        num_turns=1,
        session_id="test-session",
        result="Final report after tool use [chunk:404].",
    )


async def _fake_query_no_citations(*, prompt, options):
    yield AssistantMessage(
        content=[TextBlock(text="I cannot verify this from public sources.")], model="claude-test"
    )


async def test_run_deep_research_uses_assistant_message_text():
    async with AsyncSessionLocal() as db:
        provider = LocalHashEmbeddingProvider()
        result = await run_deep_research(
            db, "BHEL turbine tenders and competitors", provider, query_fn=_fake_query_ungrounded_multi_type_citations
        )

        assert "BHEL manufactures turbines" in result.summary


async def test_run_deep_research_rejects_ungrounded_citations_of_every_type():
    """None of chunk:404, tender:12, entity:7 were retrieved via a real tool
    call this turn (the fake never calls a tool), so all three must be
    rejected — the same anti-hallucination guarantee as Week 4, now
    covering all three reference types.
    """
    async with AsyncSessionLocal() as db:
        provider = LocalHashEmbeddingProvider()
        result = await run_deep_research(
            db, "topic", provider, query_fn=_fake_query_ungrounded_multi_type_citations
        )

        assert result.references == []
        assert result.unverifiable_reference_count == 3


async def test_run_deep_research_prefers_result_message_over_draft_text():
    async with AsyncSessionLocal() as db:
        provider = LocalHashEmbeddingProvider()
        result = await run_deep_research(db, "topic", provider, query_fn=_fake_query_result_message_wins)

        assert result.summary == "Final report after tool use [chunk:404]."
        assert "draft" not in result.summary


async def test_run_deep_research_handles_no_citations_gracefully():
    async with AsyncSessionLocal() as db:
        provider = LocalHashEmbeddingProvider()
        result = await run_deep_research(db, "topic with no evidence", provider, query_fn=_fake_query_no_citations)

        assert result.summary == "I cannot verify this from public sources."
        assert result.references == []
        assert result.unverifiable_reference_count == 0


async def test_build_deep_research_options_wires_all_three_tools_and_evidence_rules():
    async with AsyncSessionLocal() as db:
        provider = LocalHashEmbeddingProvider()
        options = build_deep_research_options(
            db, provider, retrieved_ids_by_type={"chunk": set(), "tender": set(), "entity": set()}
        )

        assert options.allowed_tools == [
            f"mcp__bhel_deep_research__{SEARCH_TOOL_NAME}",
            f"mcp__bhel_deep_research__{SEARCH_TENDERS_TOOL_NAME}",
            f"mcp__bhel_deep_research__{SEARCH_ENTITIES_TOOL_NAME}",
        ]
        assert "bhel_deep_research" in options.mcp_servers
        assert "[chunk:<id>]" in options.system_prompt
        assert "[tender:<id>]" in options.system_prompt
        assert "[entity:<id>]" in options.system_prompt
        assert "I cannot verify this from public sources" in options.system_prompt
        assert options.permission_mode == "bypassPermissions"


async def test_run_deep_research_uses_openai_compatible_loop_when_provider_is_not_anthropic(monkeypatch):
    """Same branch-wiring proof as research_agent's equivalent test: with
    query_fn=None and a non-"anthropic" provider, this must go through
    run_tool_calling_loop with all three tools, never the real SDK.
    """
    from app.agent import deep_research

    captured: dict = {}

    async def _fake_run_tool_calling_loop(config, system_prompt, user_prompt, tools, **kwargs):
        captured["config"] = config
        captured["tools"] = tools
        return "Report from an OpenAI-compatible model [entity:404]."

    monkeypatch.setattr(deep_research, "run_tool_calling_loop", _fake_run_tool_calling_loop)
    monkeypatch.setattr(deep_research.settings, "llm_provider", "openrouter")
    monkeypatch.setattr(deep_research.settings, "openrouter_api_key", "test-key")
    monkeypatch.setattr(deep_research.settings, "openrouter_model", "deepseek/deepseek-chat")

    async with AsyncSessionLocal() as db:
        provider = LocalHashEmbeddingProvider()
        result = await run_deep_research(db, "BHEL competitors", provider, query_fn=None)

        assert "Report from an OpenAI-compatible model" in result.summary
        # entity:404 was never actually retrieved via the (stubbed-out)
        # tools, so citation verification must still reject it.
        assert result.references == []
        assert result.unverifiable_reference_count == 1

    assert captured["config"].model == "deepseek/deepseek-chat"
    assert len(captured["tools"]) == 3
