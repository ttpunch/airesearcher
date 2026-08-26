from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ResearchReport(Base):
    """Output of the Deep Research workflow (app/agent/deep_research.py) —
    Week 9-10's generalization of Week 4's single-tool Ask loop into a
    multi-source-class agent (documents, tenders, KG entities) that
    synthesizes a topic-level report instead of answering one question.

    `references_json` stores the verified reference list (see
    VerifiedReference in deep_research.py) as JSON in a Text column — same
    pattern as Tender.extracted_requirements, no dedicated join table
    needed at this scale.
    """

    __tablename__ = "research_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    topic: Mapped[str] = mapped_column(String(512))
    summary: Mapped[str] = mapped_column(Text)
    references_json: Mapped[str] = mapped_column(Text)
    unverifiable_reference_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
