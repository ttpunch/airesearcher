import json
from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.deep_research import DeepResearchResult, run_deep_research
from app.core.db import get_db
from app.core.embeddings import EmbeddingProvider, get_embedding_provider
from app.models.research_report import ResearchReport
from app.schemas.research import ReferenceOut, ResearchReportOut, ResearchRequest

router = APIRouter(prefix="/api/research", tags=["research"])


def get_research_runner():
    """Same dependency-injection seam as app/routers/ask.py's
    get_ask_runner — tests override this to avoid ever invoking the real
    claude_agent_sdk.query() (see app/agent/deep_research.py's module
    docstring).
    """
    return run_deep_research


def _report_to_out(report: ResearchReport) -> ResearchReportOut:
    references = [ReferenceOut(**item) for item in json.loads(report.references_json)]
    return ResearchReportOut(
        id=report.id,
        topic=report.topic,
        summary=report.summary,
        references=references,
        unverifiable_reference_count=report.unverifiable_reference_count,
        status=report.status,
        created_at=report.created_at,
    )


@router.get("", response_model=list[ResearchReportOut])
async def list_reports(db: AsyncSession = Depends(get_db)) -> list[ResearchReportOut]:
    result = await db.execute(select(ResearchReport).order_by(ResearchReport.id.desc()))
    return [_report_to_out(r) for r in result.scalars().all()]


@router.get("/{report_id}", response_model=ResearchReportOut)
async def get_report(report_id: int, db: AsyncSession = Depends(get_db)) -> ResearchReportOut:
    report = await db.get(ResearchReport, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Research report not found")
    return _report_to_out(report)


@router.post("", response_model=ResearchReportOut, status_code=201)
async def create_report(
    payload: ResearchRequest,
    db: AsyncSession = Depends(get_db),
    embedding_provider: EmbeddingProvider = Depends(get_embedding_provider),
    runner=Depends(get_research_runner),
) -> ResearchReportOut:
    if not payload.topic or not payload.topic.strip():
        raise HTTPException(status_code=400, detail="topic must not be empty")

    result: DeepResearchResult = await runner(db, payload.topic, embedding_provider)

    references_json = json.dumps([asdict(ref) for ref in result.references])
    report = ResearchReport(
        topic=payload.topic,
        summary=result.summary,
        references_json=references_json,
        unverifiable_reference_count=result.unverifiable_reference_count,
        status="completed" if result.references else "no_evidence",
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    return _report_to_out(report)
