from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.db import get_db
from app.models.entity import Entity, Relationship
from app.schemas.entity import RelationshipWithNames

router = APIRouter(prefix="/api/relationships", tags=["relationships"])

FromEntity = aliased(Entity)
ToEntity = aliased(Entity)


@router.get("", response_model=list[RelationshipWithNames])
async def list_relationships(db: AsyncSession = Depends(get_db)) -> list[RelationshipWithNames]:
    result = await db.execute(
        select(Relationship, FromEntity.name, ToEntity.name)
        .join(FromEntity, Relationship.from_entity_id == FromEntity.id)
        .join(ToEntity, Relationship.to_entity_id == ToEntity.id)
        .order_by(Relationship.id)
    )
    return [
        RelationshipWithNames(
            id=rel.id,
            from_entity_id=rel.from_entity_id,
            to_entity_id=rel.to_entity_id,
            relation_type=rel.relation_type,
            description=rel.description,
            created_at=rel.created_at,
            from_entity_name=from_name,
            to_entity_name=to_name,
        )
        for rel, from_name, to_name in result.all()
    ]
