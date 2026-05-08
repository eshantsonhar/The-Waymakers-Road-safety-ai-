"""
RoadSoS - AI-Assisted Emergency Response Platform
Main FastAPI Application
"""
import asyncio
import uuid
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.websocket.manager import ws_manager, WSEventType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown."""
    logger.info(f"🚨 RoadSoS v{settings.APP_VERSION} starting up...")
    logger.info(f"   DEMO_MODE: {settings.DEMO_MODE}")
    logger.info(f"   Database: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else 'configured'}")

    # Try to initialize database (graceful fallback if not available)
    try:
        from app.database import init_db
        await init_db()
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.warning(f"⚠️  Database not available, running in memory-only mode: {e}")

    # Start demo simulator if DEMO_MODE is enabled
    if settings.DEMO_MODE:
        from app.demo.simulator import demo_simulator
        await demo_simulator.start()
        logger.info("✅ Demo simulator started")

    logger.info("✅ RoadSoS is ready to serve requests")

    yield

    # Shutdown
    logger.info("🛑 RoadSoS shutting down...")
    if settings.DEMO_MODE:
        from app.demo.simulator import demo_simulator
        await demo_simulator.stop()


# Create FastAPI app
app = FastAPI(
    title="RoadSoS API",
    description="AI-Assisted Emergency Response and Road Accident Intelligence Platform",
    version=settings.APP_VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and register routers
from app.api.detection import router as detection_router
from app.api.incidents import router as incidents_router
from app.api.hospitals import router as hospitals_router
from app.api.ambulances import router as ambulances_router
from app.api.risk import router as risk_router
from app.api.analytics import router as analytics_router

app.include_router(detection_router)
app.include_router(incidents_router)
app.include_router(hospitals_router)
app.include_router(ambulances_router)
app.include_router(risk_router)
app.include_router(analytics_router)


# ============================================================
# WebSocket Endpoint
# ============================================================

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """
    Main WebSocket endpoint for real-time updates.
    
    Channels: incidents, ambulances, hospitals, risk_zones, notifications
    
    Message schema:
    {
        "type": "EVENT_TYPE",
        "channel": "channel_name",
        "payload": {...},
        "timestamp": "ISO8601"
    }
    """
    await ws_manager.connect(websocket, client_id)

    try:
        # Send initial state snapshot
        from app.api.incidents import _incidents_store
        from app.api.ambulances import _ambulances_store

        snapshot = {
            "active_incidents": list(_incidents_store.values())[-20:],
            "ambulances": list(_ambulances_store.values()),
            "server_time": datetime.utcnow().isoformat(),
            "demo_mode": settings.DEMO_MODE,
            "connection_id": client_id,
        }
        await ws_manager.send_state_snapshot(client_id, snapshot)

        # Keep connection alive
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=settings.WS_HEARTBEAT_INTERVAL)
                # Handle client messages (ping/pong, subscriptions)
                if data == "ping":
                    await websocket.send_text('{"type":"pong"}')
            except asyncio.TimeoutError:
                # Send heartbeat
                try:
                    await websocket.send_text('{"type":"heartbeat","timestamp":"' +
                                              datetime.utcnow().isoformat() + '"}')
                except Exception:
                    break

    except WebSocketDisconnect:
        logger.info(f"WebSocket client {client_id} disconnected normally")
    except Exception as e:
        logger.warning(f"WebSocket error for client {client_id}: {e}")
    finally:
        await ws_manager.disconnect(client_id)


@app.websocket("/ws")
async def websocket_endpoint_default(websocket: WebSocket):
    """Default WebSocket endpoint (auto-generates client ID)."""
    client_id = str(uuid.uuid4())
    await websocket_endpoint(websocket, client_id)


# ============================================================
# Health & Status Endpoints
# ============================================================

@app.get("/")
async def root():
    """API root - returns platform info."""
    return {
        "name": "RoadSoS API",
        "version": settings.APP_VERSION,
        "description": "AI-Assisted Emergency Response and Road Accident Intelligence Platform",
        "demo_mode": settings.DEMO_MODE,
        "docs": "/api/docs",
        "websocket": "/ws",
        "status": "operational",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    from app.api.ambulances import _ambulances_store
    from app.api.incidents import _incidents_store

    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "demo_mode": settings.DEMO_MODE,
        "websocket_connections": ws_manager.connection_count,
        "active_incidents": len(_incidents_store),
        "ambulances_tracked": len(_ambulances_store),
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/api/status")
async def api_status():
    """Detailed API status."""
    return {
        "api_version": settings.APP_VERSION,
        "demo_mode": settings.DEMO_MODE,
        "websocket_connections": ws_manager.connection_count,
        "bangalore_center": {
            "latitude": settings.BANGALORE_LAT,
            "longitude": settings.BANGALORE_LON,
        },
        "detection_thresholds": {
            "crash_confirm": settings.CRASH_CONFIRM_THRESHOLD,
            "crash_suspect": settings.CRASH_SUSPECT_THRESHOLD,
        },
        "endpoints": {
            "detection": "/api/detection",
            "incidents": "/api/incidents",
            "hospitals": "/api/hospitals",
            "ambulances": "/api/ambulances",
            "risk": "/api/risk",
            "analytics": "/api/analytics",
            "websocket": "/ws",
            "docs": "/api/docs",
        },
    }
