"""API-level tests for POST /api/ask.

Overrides get_ask_runner so the real claude_agent_sdk.query() is never on
the call path here — same reasoning as test_research_agent.py.
"""

import httpx
import pytest
from asgi_lifespan import LifespanManager

from app.agent.citations import VerifiedCitation
from app.agent.research_agent import AskResponse
from app.main import app
from app.routers.ask import get_ask_runner


@pytest.fixture
async def client(s3_env):
    async with LifespanManager(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            yield c
    app.dependency_overrides.pop(get_ask_runner, None)


async def _stub_verified_answer(db, question, embedding_provider):
    return AskResponse(
        answer="BHEL manufactures thermal power turbines [FACT] [chunk:1].",
        citations=[
            VerifiedCitation(
                chunk_id=1,
                content="BHEL manufactures thermal power turbines.",
                source_name="BHEL — Home",
                source_url="https://www.bhel.com/",
                source_tier="T1",
                document_id=42,
            )
        ],
        unverifiable_citation_count=0,
    )


async def _stub_unverifiable_answer(db, question, embedding_provider):
    return AskResponse(answer="Some claim [chunk:999].", citations=[], unverifiable_citation_count=1)


async def _stub_no_evidence_answer(db, question, embedding_provider):
    return AskResponse(answer="I cannot verify this from public sources.", citations=[], unverifiable_citation_count=0)


async def test_ask_returns_verified_true_when_all_citations_grounded(client):
    app.dependency_overrides[get_ask_runner] = lambda: _stub_verified_answer

    resp = await client.post("/api/ask", json={"question": "What does BHEL manufacture?"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["verified"] is True
    assert body["unverifiable_citation_count"] == 0
    assert len(body["citations"]) == 1
    assert body["citations"][0]["source_tier"] == "T1"


async def test_ask_returns_verified_false_when_citation_unverifiable(client):
    app.dependency_overrides[get_ask_runner] = lambda: _stub_unverifiable_answer

    resp = await client.post("/api/ask", json={"question": "Some question"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["verified"] is False
    assert body["unverifiable_citation_count"] == 1
    assert body["citations"] == []


async def test_ask_returns_verified_false_for_honest_no_evidence_answer(client):
    """Zero citations is not the same as 'verified' — it's honest
    uncertainty, and the response must not claim otherwise.
    """
    app.dependency_overrides[get_ask_runner] = lambda: _stub_no_evidence_answer

    resp = await client.post("/api/ask", json={"question": "Some unanswerable question"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["answer"] == "I cannot verify this from public sources."
    assert body["verified"] is False


async def test_ask_rejects_empty_question(client):
    resp = await client.post("/api/ask", json={"question": "   "})
    assert resp.status_code == 400
