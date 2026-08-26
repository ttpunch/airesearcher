from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core import storage
from app.core.config import settings
from app.core.db import AsyncSessionLocal
from app.core.seed import seed_sources
from app.routers import documents, health, sources


@asynccontextmanager
async def lifespan(app: FastAPI):
    storage.ensure_bucket()
    async with AsyncSessionLocal() as db:
        await seed_sources(db)
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
