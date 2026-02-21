"""
BluePrint — FastAPI application entry point.
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from backend.database import init_db
from backend.config import settings
from backend.services.scheduler import start_scheduler, stop_scheduler
from backend.services.log_streamer import install_handler, register, unregister

from backend.routers.dashboard import router as dashboard_router
from backend.routers.assets import router as assets_router
from backend.routers.strategies import router as strategies_router
from backend.routers.setups import router as setups_router
from backend.routers.scans import router as scans_router
from backend.routers.journal import router as journal_router
from backend.routers.backtester_router import router as backtester_router
from backend.routers.webhooks import router as webhooks_router
from backend.routers.chart_data import router as chart_data_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("blueprint")

# Install WebSocket log handler so every log line is streamed to the frontend
install_handler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    logger.info("BluePrint starting up...")
    init_db()
    start_scheduler()
    logger.info(f"Server running on http://{settings.host}:{settings.port}")
    yield
    # Shutdown
    stop_scheduler()
    logger.info("BluePrint shutting down.")


app = FastAPI(
    title="BluePrint",
    description="Crypto Swing Trading Scanner",
    version="1.0.0",
    lifespan=lifespan,
)

# Register API routers
app.include_router(dashboard_router)
app.include_router(assets_router)
app.include_router(strategies_router)
app.include_router(setups_router)
app.include_router(scans_router)
app.include_router(journal_router)
app.include_router(backtester_router)
app.include_router(webhooks_router)
app.include_router(chart_data_router)

# ─── WebSocket: live log stream ──────────────────────────────────────────────
@app.websocket("/ws/logs")
async def ws_logs(ws: WebSocket):
    await register(ws)
    try:
        while True:
            # Keep the connection open; we only send, but must read to detect close
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        unregister(ws)


# Serve frontend static files
frontend_dir = Path(__file__).parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

    @app.get("/")
    async def serve_frontend():
        return FileResponse(str(frontend_dir / "index.html"))

    @app.get("/{path:path}")
    async def serve_spa(path: str):
        """Catch-all to serve the SPA for client-side routing."""
        file_path = frontend_dir / path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(frontend_dir / "index.html"))
