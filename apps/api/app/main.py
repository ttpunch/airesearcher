from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core import storage
from app.core.config import settings
from app.core.db import AsyncSessionLocal
from app.core.seed import (
    seed_competitor_sources,
    seed_entities,
    seed_gem_tenders,
    seed_government_sources,
    seed_opportunities,
    seed_sources,
)
from app.routers import (
    ask,
    dashboard,
    documents,
    entities,
    health,
    npp,
    opportunities,
    relationships,
    research,
    search,
    sources,
    tenders,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    storage.ensure_bucket()
    async with AsyncSessionLocal() as db:
        await seed_sources(db)
        await seed_competitor_sources(db)
        await seed_government_sources(db)
        await seed_gem_tenders(db)
        await seed_entities(db)
        await seed_opportunities(db)
    yield


app = FastAPI(title="AI Researcher API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(sources.router)
app.include_router(documents.router)
app.include_router(search.router)
app.include_router(ask.router)
app.include_router(tenders.router)
app.include_router(entities.router)
app.include_router(relationships.router)
app.include_router(research.router)
app.include_router(opportunities.router)
app.include_router(dashboard.router)
app.include_router(npp.router)
