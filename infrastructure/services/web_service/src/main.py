import logging
import signal
import sys
import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

# Add project root to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../'))

from shared.clients.database_client import db_client
from shared.clients.bot_client import bot_client
from shared.clients.media_client import media_client
from config import get_config
from api.routers import (
    users_router,
    auth_router,
    feedback_router,
    rental_objects_router,
    poll_router,
    service_tickets_router,
    service_ticket_logs_router,
    rental_spaces_router,
    space_views_router,
    media_router,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages the application lifecycle: connect/disconnect database client."""
    logger.info("WebService starting up...")
    try:
        await db_client.connect()
        logger.info("Database client connected via HTTP.")
    except Exception as e:
        logger.critical(f"Failed to connect database client during startup: {e}", exc_info=True)
    try:
        await bot_client.connect()
        logger.info("Bot client connected via HTTP.")
    except Exception as e:
        logger.warning(f"Failed to connect bot client during startup: {e}", exc_info=True)
    try:
        await media_client.connect()
        logger.info("Media client connected.")
    except Exception as e:
        logger.warning(f"Failed to connect media client during startup: {e}", exc_info=True)
    yield
    logger.info("WebService shutting down...")
    await media_client.disconnect()
    await bot_client.disconnect()
    await db_client.disconnect()
    logger.info("Clients disconnected.")


# Create FastAPI application
app = FastAPI(
    title="Nord City Web API",
    description="REST API gateway for the Nord City microservices architecture.",
    version="3.0.0",
    lifespan=lifespan,
    redirect_slashes=False,
)

# Configure CORS
try:
    config = get_config()
    cors_origins = list(config.cors_origins)
    public_origin = os.getenv("PUBLIC_ORIGIN")
    public_origins = os.getenv("PUBLIC_ORIGINS")
    if public_origin:
        cors_origins.append(public_origin.strip())
    if public_origins:
        cors_origins.extend([o.strip() for o in public_origins.split(",") if o.strip()])
    # De-duplicate while preserving order
    seen = set()
    cors_origins = [o for o in cors_origins if not (o in seen or seen.add(o))]
except Exception as e:
    logger.warning(f"Could not load CORS config, using safe defaults. Error: {e}")
    cors_origins = ["http://localhost:3000"]

logger.info(f"CORS enabled for origins: {cors_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# --- Include explicit routers under /api/v1 ---
API_PREFIX = "/api/v1"
app.include_router(users_router, prefix=API_PREFIX)
app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(feedback_router, prefix=API_PREFIX)
app.include_router(rental_objects_router, prefix=API_PREFIX)
app.include_router(poll_router, prefix=API_PREFIX)
app.include_router(service_tickets_router, prefix=API_PREFIX)
app.include_router(service_ticket_logs_router, prefix=API_PREFIX)
app.include_router(rental_spaces_router, prefix=API_PREFIX)
app.include_router(space_views_router, prefix=API_PREFIX)
app.include_router(media_router, prefix=API_PREFIX)


# --- Service-level endpoints (outside /api/v1) ---
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def root():
    return (
        "<html><body><h1>Nord City Web Service API</h1>"
        "<p>Navigate to <a href='/docs'>/docs</a> for API documentation.</p>"
        "</body></html>"
    )


@app.get("/health")
async def health_check():
    """Health check for the web service and its database client connection."""
    is_connected = db_client._connected
    return {
        "status": "healthy" if is_connected else "degraded",
        "service": "web_service",
        "database_client_connected": is_connected,
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler to catch unhandled errors."""
    logger.error(f"Unhandled exception for {request.url.path}: {exc}", exc_info=True)
    origin = request.headers.get("origin", "")
    response = JSONResponse(
        status_code=500,
        content={"detail": "An unexpected internal server error occurred."},
    )
    if origin in cors_origins or "*" in cors_origins:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
    return response


def signal_handler(signum, frame):
    logger.info(f"Received signal {signum}, shutting down.")


# --- Main Execution ---
if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        service_config = get_config().service
        root_path = os.getenv("ROOT_PATH", "")
        logger.info(
            f"Starting server at http://{service_config.host}:{service_config.port}"
            f" with root_path={root_path if root_path else '(none)'}"
        )
        uvicorn.run(
            "main:app",
            host=service_config.host,
            port=service_config.port,
            root_path=root_path,
            log_level="info",
            reload=False,
        )
    except Exception as e:
        logger.critical(f"Failed to start server: {e}", exc_info=True)
        sys.exit(1)
