import uuid

from sqlalchemy import delete, select

from app.core.db import AsyncSessionLocal
from app.models.entity import Entity, Relationship


async def test_entity_stores_and_retrieves():
    async with AsyncSessionLocal() as db:
        name = f"Test Entity {uuid.uuid4()}"
        entity = Entity(name=name, entity_type="technology", description="A test technology entity.")
        db.add(entity)
        await db.commit()
        await db.refresh(entity)

        try:
            assert entity.id is not None
            result = await db.execute(select(Entity).where(Entity.name == name))
            fetched = result.scalar_one()
            assert fetched.entity_type == "technology"
            assert fetched.source_id is None
        finally:
            await db.execute(delete(Entity).where(Entity.id == entity.id))
            await db.commit()


async def test_relationship_links_two_entities():
    async with AsyncSessionLocal() as db:
        a = Entity(name=f"Entity A {uuid.uuid4()}", entity_type="organization")
        b = Entity(name=f"Entity B {uuid.uuid4()}", entity_type="competitor")
        db.add_all([a, b])
        await db.commit()
        await db.refresh(a)
        await db.refresh(b)

        try:
            rel = Relationship(from_entity_id=a.id, to_entity_id=b.id, relation_type="competes_with")
            db.add(rel)
            await db.commit()
            await db.refresh(rel)

            assert rel.id is not None

            result = await db.execute(select(Relationship).where(Relationship.from_entity_id == a.id))
            fetched = result.scalar_one()
            assert fetched.to_entity_id == b.id
            assert fetched.relation_type == "competes_with"
        finally:
            await db.execute(delete(Relationship).where(Relationship.from_entity_id == a.id))
            await db.execute(delete(Entity).where(Entity.id.in_([a.id, b.id])))
            await db.commit()


async def test_entity_name_and_type_unique_together():
    async with AsyncSessionLocal() as db:
        name = f"Duplicate Entity {uuid.uuid4()}"
        e1 = Entity(name=name, entity_type="technology")
        db.add(e1)
        await db.commit()
        await db.refresh(e1)

        try:
            # Same name, different type — allowed (compound uniqueness).
            e2 = Entity(name=name, entity_type="competitor")
            db.add(e2)
            await db.commit()
            await db.refresh(e2)
            assert e2.id != e1.id

            await db.execute(delete(Entity).where(Entity.id == e2.id))
            await db.commit()
        finally:
            await db.execute(delete(Entity).where(Entity.id == e1.id))
            await db.commit()
