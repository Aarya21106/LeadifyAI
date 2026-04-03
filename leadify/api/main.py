from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

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
app.include_router(leads.router, prefix="/api/leads", tags=["Leads"])
app.include_router(queue.router, prefix="/api/queue", tags=["Queue"])
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(agents.router, prefix="/api/agents", tags=["Agents"])

@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "version": "1.0.0"}

# Serve built React App
ui_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ui", "dist")

if os.path.isdir(os.path.join(ui_path, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(ui_path, "assets")), name="assets")

@app.get("/{catchall:path}", tags=["Frontend"])
async def serve_react_app(catchall: str):
    file_path = os.path.join(ui_path, catchall)
    if os.path.isfile(file_path):
        return FileResponse(file_path)
    
    index_path = os.path.join(ui_path, "index.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path)
    return {"error": "Frontend UI not built yet. Run npm run build in leadify/ui."}
