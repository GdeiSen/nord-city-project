import asyncio
import logging
import os
import signal
import sys
from typing import Dict, Any

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

# --- Path Setup ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
sys.path.append(project_root)

from config import get_config
from database.database_manager import DatabaseManager
from shared.utils.converter import Converter
from shared.schemas.rpc import get_rpc_schema

# --- Model Imports for Registration ---
from models.user import User
from models.user_auth import UserAuth
from models.feedback import Feedback
from models.object import Object
from models.poll_answer import PollAnswer
from models.service_ticket import ServiceTicket
from models.guest_parking_request import GuestParkingRequest
from models.audit_log import AuditLog
from models.space import Space
from models.space_view import SpaceView
from models.otp_code import OtpCode

# --- Service Imports for Registration ---
from services.user_service import UserService
from services.auth_service import AuthService
from services.otp_service import OtpService
from services.feedback_service import FeedbackService
from services.object_service import ObjectService
from services.poll_service import PollService
from services.space_service import SpaceService
from services.service_ticket_service import ServiceTicketService
from services.guest_parking_service import GuestParkingService
from services.audit_log_service import AuditLogService
from services.space_view_service import SpaceViewService

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# --- Pydantic models for the internal RPC endpoint ---

class RPCRequest(BaseModel):
    """Internal RPC request body."""
    service: str
    method: str
    params: Dict[str, Any] = {}


class RPCResponse(BaseModel):
    """Internal RPC response body."""
    success: bool
    data: Any = None
    error: str | None = None


# --- Application ---

db_manager = DatabaseManager()


def _register_resources():
    """Explicitly registers all models and services."""
    logger.info("Registering database models and services...")

    models_to_register = [
        User, UserAuth, Feedback, Object, PollAnswer,
        ServiceTicket, GuestParkingRequest, AuditLog, Space, SpaceView, OtpCode,
    ]
    for model in models_to_register:
        db_manager.repositories.register(model)

    services_to_register = {
        "user": UserService,
        "auth": AuthService,
        "feedback": FeedbackService,
        "object": ObjectService,
        "poll": PollService,
        "space": SpaceService,
        "service_ticket": ServiceTicketService,
        "guest_parking": GuestParkingService,
        "audit_log": AuditLogService,
        "space_view": SpaceViewService,
        "otp": OtpService,
    }
    for name, service_class in services_to_register.items():
        db_manager.services.register(name, service_class(db_manager))

    logger.info("All resources registered successfully.")


async def _ensure_default_object():
    """
    Ensures that Object with id=1 exists at startup.
    Creates it with starter information if it does not exist.
    Required for normal operation of the entire system.
    """
    from sqlalchemy import text

    obj_repo = db_manager.repositories.get(Object)
    async with db_manager.get_session() as session:
        existing = await obj_repo.get_by_id(session, entity_id=1)
        if existing is not None:
            logger.info("Default object (id=1) already exists, skipping creation.")
            return

        default_obj = Object(
            id=1,
            name="Nord City",
            address="",
            description="",
            photos=[],
            status="ACTIVE",
        )
        await obj_repo.create(session, obj_in=default_obj)
        # Sync PostgreSQL sequence so next auto-generated id is 2+
        await session.execute(
            text("SELECT setval('objects_id_seq', (SELECT COALESCE(MAX(id), 1) FROM objects))")
        )
        await session.commit()

    logger.info("Created default object with id=1 for system initialization.")


async def _rpc_handler(request: dict) -> dict:
    """Universal RPC handler that processes all incoming requests."""
    try:
        service_name = request.get("service")
        method_name = request.get("method")
        params = request.get("params", {})

        if not service_name or not method_name:
            return {"success": False, "error": "Request must include 'service' and 'method'."}

        service_instance = db_manager.services.get(service_name)
        method_to_call = getattr(service_instance, method_name, None)

        if not method_to_call or not asyncio.iscoroutinefunction(method_to_call):
            return {"success": False, "error": f"Method '{method_name}' not found in service '{service_name}'."}

        # Валидация model_data / update_data через Pydantic-схемы (если зарегистрированы)
        for param_name in ("model_data", "update_data"):
            if param_name not in params:
                continue
            schema_cls = get_rpc_schema(service_name, method_name, param_name)
            if schema_cls is not None:
                validated = schema_cls.model_validate(params[param_name])
                params[param_name] = validated.model_dump(exclude_none=(param_name == "update_data"))

        # model_data → model_instance (RPC-схема или Converter)
        if "model_data" in params:
            model_class = service_instance.model_class
            params["model_instance"] = Converter.from_dict(model_class, params.pop("model_data"))

        result = await method_to_call(**params)

        return {"success": True, "data": Converter.to_dict(result)}
    except Exception as e:
        logger.error(f"Unhandled exception in RPC handler for {request}: {e}", exc_info=True)
        return {"success": False, "error": f"An internal server error occurred: {e}"}


# --- FastAPI lifespan ---

from contextlib import asynccontextmanager

from shared.clients.media_client import media_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Database Service (HTTP)...")
    await db_manager.initialize_db()
    _register_resources()
    await _ensure_default_object()
    try:
        await db_manager.services.get("guest_parking").init_reminder_cache()
    except Exception as e:
        logger.warning("Guest parking reminder cache init failed: %s", e)
    try:
        await media_client.connect()
        logger.info("Media client connected for cleanup.")
    except Exception as e:
        logger.warning("Media client not available (cleanup will be skipped): %s", e)
    logger.info("Database Service ready.")
    yield
    logger.info("Shutting down Database Service...")
    await media_client.disconnect()
    await db_manager.db_connection.close()
    logger.info("Database Service stopped.")


app = FastAPI(
    title="Nord City Database Service (Internal)",
    description="Internal HTTP RPC endpoint for database operations.",
    version="3.0.0",
    lifespan=lifespan,
)


@app.post("/internal/rpc", response_model=RPCResponse)
async def rpc_endpoint(request: RPCRequest):
    """
    Single internal RPC endpoint. All database operations go through here.
    Body: {service, method, params}
    Response: {success, data, error}
    """
    result = await _rpc_handler(request.model_dump())
    return result


@app.get("/health")
async def health_check():
    """Health check for the database service."""
    db_healthy = await db_manager.db_connection.health_check()
    return {
        "status": "healthy" if db_healthy else "degraded",
        "service": "database_service",
        "database_connected": db_healthy,
    }


# --- Signal handling ---

def signal_handler(signum, frame):
    logger.info(f"Received signal {signum}")


# --- Main Execution ---
if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    config = get_config()
    host = os.getenv("DATABASE_SERVICE_HOST", "0.0.0.0")
    port = int(os.getenv("DATABASE_SERVICE_PORT", "8001"))

    logger.info(f"Starting Database Service HTTP server on {host}:{port}")
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        log_level="info",
        reload=False,
    )
