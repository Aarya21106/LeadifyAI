from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from leadify.common.settings import settings
from leadify.db.session import engine
from leadify.db.models import Base
from leadify.api.routes import leads, queue, auth, agents
from leadify.orchestrator.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create DB tables on startup, start scheduler, dispose engine on shutdown."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await start_scheduler()
    yield
    await stop_scheduler()
    await engine.dispose()


app = FastAPI(
    title="Leadify AI",
    description="Multi-agent AI system for autonomous cold email lead management",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow frontend origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(leads.router, prefix="/leads", tags=["Leads"])
app.include_router(queue.router, prefix="/queue", tags=["Queue"])
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(agents.router, prefix="/agents", tags=["Agents"])


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok"}
