from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.entity import Entity, Relationship
from app.models.source import Source
from app.schemas.entity import EntityCreate, EntityDetail, EntityRead

router = APIRouter(prefix="/api/entities", tags=["entities"])


def _to_entity_read(entity: Entity, source: Source | None) -> EntityRead:
    return EntityRead(
        id=entity.id,
        name=entity.name,
        entity_type=entity.entity_type,
        description=entity.description,
        source_id=entity.source_id,
        source_name=source.name if source else None,
        source_url=source.url if source else None,
        created_at=entity.created_at,
    )


@router.get("", response_model=list[EntityRead])
async def list_entities(entity_type: str | None = None, db: AsyncSession = Depends(get_db)) -> list[EntityRead]:
    query = select(Entity, Source).outerjoin(Source, Entity.source_id == Source.id).order_by(Entity.id)
    if entity_type is not None:
        query = query.where(Entity.entity_type == entity_type)
    result = await db.execute(query)
    return [_to_entity_read(entity, source) for entity, source in result.all()]


@router.get("/{entity_id}", response_model=EntityDetail)
async def get_entity(entity_id: int, db: AsyncSession = Depends(get_db)) -> EntityDetail:
    result = await db.execute(
        select(Entity, Source).outerjoin(Source, Entity.source_id == Source.id).where(Entity.id == entity_id)
    )
    row = result.first()
    if row is None:
        raise HTTPException(status_code=404, detail="Entity not found")
    entity, source = row

    rel_result = await db.execute(
        select(Relationship).where(
            or_(Relationship.from_entity_id == entity_id, Relationship.to_entity_id == entity_id)
        )
    )
    relationships = list(rel_result.scalars().all())

    base = _to_entity_read(entity, source)
    return EntityDetail(**base.model_dump(), relationships=relationships)


@router.post("", response_model=EntityRead, status_code=201)
async def create_entity(payload: EntityCreate, db: AsyncSession = Depends(get_db)) -> EntityRead:
    entity = Entity(**payload.model_dump())
    db.add(entity)
    await db.commit()
    await db.refresh(entity)

    source = await db.get(Source, entity.source_id) if entity.source_id else None
    return _to_entity_read(entity, source)
