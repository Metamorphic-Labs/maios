# maios/api/main.py
from contextlib import asynccontextmanager

from fastapi import FastAPI

from maios.api.routes import agents, health, projects
from maios.core.config import settings
from maios.core.database import close_db, init_db
from maios.core.redis import close_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    await init_db()
    yield
    # Shutdown
    await close_db()
    await close_redis()


app = FastAPI(
    title="MAIOS",
    description="Metamorphic AI Orchestration System",
    version="0.1.0",
    lifespan=lifespan,
)

# Include routers
app.include_router(health.router, tags=["health"])
app.include_router(projects.router, tags=["projects"])
app.include_router(agents.router, tags=["agents"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "MAIOS",
        "version": "0.1.0",
        "status": "running",
    }
