from fastapi import FastAPI

from app.routers import health

app = FastAPI(title="AI Researcher API")

app.include_router(health.router)
