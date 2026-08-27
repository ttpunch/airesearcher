from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EntityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    entity_type: str
    description: str | None
    source_id: int | None
    source_name: str | None = None
    source_url: str | None = None
    created_at: datetime


class RelationshipRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    from_entity_id: int
    to_entity_id: int
    relation_type: str
    description: str | None
    created_at: datetime


class RelationshipWithNames(RelationshipRead):
    from_entity_name: str
    to_entity_name: str


class EntityDetail(EntityRead):
    relationships: list[RelationshipRead]


class EntityCreate(BaseModel):
    name: str
    entity_type: str
    description: str | None = None
    source_id: int | None = None
