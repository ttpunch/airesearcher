from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Source(Base):
    """A registered origin the crawler pulls from, or a synthetic origin
    (e.g. "User Upload") that manually-uploaded documents are attributed to.

    `tier` follows the evidence system's trust scale from the strategy
    report (docs/research/bhel-ai-strategy.html §17): T1 (official
    BHEL/government/regulator) down to T6 (other/aggregator), plus "UP"
    for user-provided uploads not yet cross-verified against a known tier.
    """

    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    url: Mapped[str] = mapped_column(String(2048), unique=True)
    source_type: Mapped[str] = mapped_column(String(64))
    tier: Mapped[str] = mapped_column(String(8))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_crawled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
