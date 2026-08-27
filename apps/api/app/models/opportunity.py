from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Opportunity(Base):
    """A strategic initiative recommendation — RECOMMENDATION-tagged output
    per AGENTS.md's hard constraint ("Recommendation-tagged output requires
    human approval before acting on it"). `status` starts at "proposed"
    and only moves to "approved"/"rejected" via an explicit human action
    through POST /api/opportunities/{id}/approve or /reject — there is no
    path that auto-approves one. `approved_by` is a plain free-text field,
    not a real auth system; see AGENTS.md's Week 11-12 note for that
    acknowledged gap.

    Seeded from docs/research/bhel-ai-strategy.html's Top 10 Strategic
    Initiatives (§10) and Business Value/ROI Framework (§23) — real,
    already-sourced content from this project's own research phase, not
    newly fabricated for this table.
    """

    __tablename__ = "opportunities"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    feasibility: Mapped[str] = mapped_column(String(8))
    strategic_value: Mapped[str] = mapped_column(String(32))
    weighted_score: Mapped[int] = mapped_column(Integer)
    tech_summary: Mapped[str] = mapped_column(Text)
    timeline: Mapped[str] = mapped_column(String(64))
    risk: Mapped[str] = mapped_column(Text)
    source_section: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(16), default="proposed")
    approved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
