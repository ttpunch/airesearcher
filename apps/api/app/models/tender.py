from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Tender(Base):
    """A single tender notice, attributed to a Source (the portal it was
    found on) and optionally a Document (the notice/PDF it was extracted
    from). `extracted_requirements` is populated by
    app/processing/tender_extraction.py's deterministic extractor — never
    fabricated, and left null until extraction actually runs.
    """

    __tablename__ = "tenders"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"))
    document_id: Mapped[int | None] = mapped_column(ForeignKey("documents.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(512))
    tender_ref: Mapped[str | None] = mapped_column(String(128), nullable=True)
    organization: Mapped[str] = mapped_column(String(255))
    url: Mapped[str] = mapped_column(String(2048))
    published_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    closing_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    estimated_value: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="unknown")
    extracted_requirements: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
