"""Snapshots NPP data into the knowledge graph (Entity/Relationship) so it
shows up on the existing /graph and /dashboard pages alongside BHEL's
other tracked entities, rather than being reachable only through the live
MCP tools (app/portals/npp/tools.py) or the standalone MCP server.

This is deliberately narrower than NPP's full dataset. The 578 operating
stations and ~478 already-commissioned station-map records stay a
live-query concern — ingesting them as ~1,000 new graph nodes would swamp
a knowledge graph currently sized at 9 entities and isn't what a reader
of /graph or /dashboard would expect to see grow by two orders of
magnitude from one sync call. What's ingested here is the two things
that are naturally graph-shaped competitive intelligence, matching the
KG's existing spirit (competitors, technologies):

- `power_organization` — every organization named as operating a station
  or developing an under-construction project, with a description
  aggregating real counts/capacity (never LLM-generated).
- `power_project` — under-construction projects only (the "pipeline"),
  not commissioned ones (the installed base already has no per-station
  ingest here either, for the same volume reason).

`developed_by` relationships connect a project to its organization only
when NPP's own data names one — most under-construction records don't
(verified against real captured data), so most projects land as
unconnected nodes rather than a fabricated edge.

This module owns the one DB-facing seam in app/portals/ — see that
package's docstring for why the rest of the scaffold stays free of
app.models/app.core.db imports.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entity import Entity, Relationship
from app.models.source import Source
from app.portals.npp.client import NppClient
from app.portals.npp.endpoints import ATTRIBUTION, DASHBOARD_URL

NPP_SOURCE_NAME = "National Power Portal (NPP)"


@dataclass
class NppSyncResult:
    source_created: bool
    organizations_created: int = 0
    organizations_updated: int = 0
    projects_created: int = 0
    projects_updated: int = 0
    relationships_created: int = 0
    retrieved_at: datetime = field(default_factory=lambda: datetime.now(UTC))


async def _get_or_create_source(db: AsyncSession) -> tuple[Source, bool]:
    result = await db.execute(select(Source).where(Source.url == DASHBOARD_URL))
    source = result.scalar_one_or_none()
    if source is not None:
        return source, False
    source = Source(name=NPP_SOURCE_NAME, url=DASHBOARD_URL, source_type="government_portal", tier="T1")
    db.add(source)
    await db.flush()
    return source, True


async def _upsert_entity(
    db: AsyncSession, name: str, entity_type: str, description: str, source_id: int | None
) -> tuple[Entity, bool, bool]:
    """Get-or-create by (name, entity_type) like app/core/seed.py's
    seeders, but also refreshes the description on an existing row so a
    re-sync picks up changed capacity/status — the seeders never update
    because their seed data is static; NPP's isn't. Returns
    (entity, created, updated).
    """
    result = await db.execute(select(Entity).where(Entity.name == name, Entity.entity_type == entity_type))
    entity = result.scalar_one_or_none()
    if entity is None:
        entity = Entity(name=name, entity_type=entity_type, description=description, source_id=source_id)
        db.add(entity)
        await db.flush()
        return entity, True, False
    if entity.description != description:
        entity.description = description
        return entity, False, True
    return entity, False, False


async def _get_or_create_relationship(db: AsyncSession, from_entity_id: int, to_entity_id: int, relation_type: str) -> bool:
    result = await db.execute(
        select(Relationship).where(
            Relationship.from_entity_id == from_entity_id,
            Relationship.to_entity_id == to_entity_id,
            Relationship.relation_type == relation_type,
        )
    )
    if result.scalar_one_or_none() is not None:
        return False
    db.add(Relationship(from_entity_id=from_entity_id, to_entity_id=to_entity_id, relation_type=relation_type))
    return True


async def sync_npp(db: AsyncSession, client: NppClient) -> NppSyncResult:
    source, source_created = await _get_or_create_source(db)
    source.last_crawled_at = datetime.now(UTC)

    stations = await client.stations()
    projects = await client.projects()
    under_construction = [p for p in projects if p.status == "under_construction"]

    result = NppSyncResult(
        source_created=source_created,
        retrieved_at=stations[0].retrieved_at if stations else datetime.now(UTC),
    )

    # Aggregate real counts per organization from both datasets before
    # creating anything, so an org that both operates stations and has a
    # project in the pipeline gets one entity with one combined
    # description, not two competing upserts.
    org_stats: dict[str, dict[str, float]] = {}
    for station in stations:
        name = station.org_short_name or station.company_name
        if not name:
            continue
        stats = org_stats.setdefault(name, {"stations": 0, "mw": 0.0, "projects": 0})
        stats["stations"] += 1
        stats["mw"] += station.installed_capacity_mw or 0.0
    for project in under_construction:
        if not project.organization:
            continue
        stats = org_stats.setdefault(project.organization, {"stations": 0, "mw": 0.0, "projects": 0})
        stats["projects"] += 1

    org_entities: dict[str, Entity] = {}
    for name, stats in org_stats.items():
        parts = []
        if stats["stations"]:
            parts.append(f"Operates {int(stats['stations'])} power station(s) totalling {round(stats['mw'])} MW installed capacity")
        if stats["projects"]:
            parts.append(f"Developing {int(stats['projects'])} under-construction project(s)")
        description = "; ".join(parts) + f". {ATTRIBUTION}"
        entity, created, updated = await _upsert_entity(db, name, "power_organization", description, source.id)
        org_entities[name] = entity
        result.organizations_created += int(created)
        result.organizations_updated += int(updated)

    for project in under_construction:
        bits = [f"{project.capacity_mw:.0f} MW" if project.capacity_mw else "capacity unknown"]
        bits.append(project.state or "state unknown")
        if project.expected_date and project.expected_date_kind:
            bits.append(f"expected {project.expected_date.isoformat()} ({project.expected_date_kind})")
        if project.cost_overrun.raw:
            bits.append(f"cost overrun {project.cost_overrun.raw}")
        description = ", ".join(bits) + f". {ATTRIBUTION}"
        entity, created, updated = await _upsert_entity(db, project.project_name, "power_project", description, source.id)
        result.projects_created += int(created)
        result.projects_updated += int(updated)

        if project.organization and project.organization in org_entities:
            created_rel = await _get_or_create_relationship(
                db, entity.id, org_entities[project.organization].id, "developed_by"
            )
            result.relationships_created += int(created_rel)

    await db.commit()
    return result
