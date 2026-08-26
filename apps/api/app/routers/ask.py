from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.research_agent import AskResponse, run_research_query
from app.core.db import get_db
from app.core.embeddings import EmbeddingProvider, get_embedding_provider
from app.schemas.ask import AskRequest, AskResponseOut, CitationOut

router = APIRouter(prefix="/api", tags=["ask"])


def get_ask_runner():
    """A seam for dependency-injection: tests override this to avoid ever
    invoking the real claude_agent_sdk.query() (subprocess call, real API
    usage) — see app/agent/research_agent.py's module docstring.
    """
    return run_research_query


@router.post("/ask", response_model=AskResponseOut)
async def ask(
    payload: AskRequest,
    db: AsyncSession = Depends(get_db),
    embedding_provider: EmbeddingProvider = Depends(get_embedding_provider),
    runner=Depends(get_ask_runner),
) -> AskResponseOut:
    if not payload.question or not payload.question.strip():
        raise HTTPException(status_code=400, detail="question must not be empty")

    result: AskResponse = await runner(db, payload.question, embedding_provider)

    return AskResponseOut(
        answer=result.answer,
        citations=[
            CitationOut(
                chunk_id=c.chunk_id,
                content=c.content,
                source_name=c.source_name,
                source_url=c.source_url,
                source_tier=c.source_tier,
                document_id=c.document_id,
            )
            for c in result.citations
        ],
        unverifiable_citation_count=result.unverifiable_citation_count,
        verified=bool(result.citations) and result.unverifiable_citation_count == 0,
    )
