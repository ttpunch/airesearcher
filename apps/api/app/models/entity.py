from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Entity(Base):
    """A node in the knowledge graph — plain Postgres table per the
    architecture decision in AGENTS.md (query patterns here are shallow
    1-2 hop lookups, not deep graph traversal, so a graph database isn't
    justified). `entity_type` is a free string ("organization",
    "competitor", "technology", ...) rather than an enum, matching
    Source.source_type's convention elsewhere in this codebase.
    `source_id` is set when the entity has a real, verifiable origin (a
    company's official site); left null for concept entities like a
    named technology that isn't itself a crawlable source.
    """

    __tablename__ = "entities"
    __table_args__ = (UniqueConstraint("name", "entity_type", name="uq_entities_name_type"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    entity_type: Mapped[str] = mapped_column(String(64))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Relationship(Base):
    """A directed, typed edge between two Entities."""

    __tablename__ = "relationships"

    id: Mapped[int] = mapped_column(primary_key=True)
    from_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id"))
    to_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id"))
    relation_type: Mapped[str] = mapped_column(String(64))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
