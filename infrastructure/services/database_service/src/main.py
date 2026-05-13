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
from shared.permissions import (
    ADMIN_DEFAULT_PERMISSIONS,
    ADMIN_ROLE_CODE,
    DEFAULT_PERMISSIONS,
    EVERYONE_DEFAULT_PERMISSIONS,
    EVERYONE_ROLE_CODE,
    SUPER_ADMIN_ROLE_CODE,
)

# --- Model Imports for Registration ---
from models.user import User
from models.user_auth import UserAuth
from models.role import Role, RolePermission
from models.permission import Permission
from models.user_role import UserRole
from models.contract import Contract, UserContract
from models.feedback import Feedback
from models.service_ticket_feedback_ref import ServiceTicketFeedbackRef
from models.dynamic_dialog_binding import DynamicDialogBinding
from models.object import Object
from models.poll_answer import PollAnswer
from models.service_ticket import ServiceTicket
from models.guest_parking_request import GuestParkingRequest
from models.guest_parking_settings import GuestParkingSettings
from models.audit_log import AuditLog
from models.bot_message_ref import BotMessageRef
from models.space import Space
from models.space_view import SpaceView
from models.otp_code import OtpCode
from models.storage_file import StorageFile
from models.telegram_chat import TelegramChat

# --- Service Imports for Registration ---
from services.user_service import UserService
from services.auth_service import AuthService
from services.role_service import RoleService
from services.permission_service import PermissionService
from services.contract_service import ContractService
from services.otp_service import OtpService
from services.feedback_service import FeedbackService
from services.service_ticket_feedback_ref_service import ServiceTicketFeedbackRefService
from services.dynamic_dialog_binding_service import DynamicDialogBindingService
from services.object_service import ObjectService
from services.poll_service import PollService
from services.space_service import SpaceService
from services.service_ticket_service import ServiceTicketService
from services.guest_parking_service import GuestParkingService
from services.guest_parking_settings_service import GuestParkingSettingsService
from services.audit_log_service import AuditLogService
from services.bot_message_ref_service import BotMessageRefService
from services.space_view_service import SpaceViewService
from services.storage_file_service import StorageFileService
from services.telegram_chat_service import TelegramChatService

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
        User, UserAuth, Role, Permission, RolePermission, UserRole, Contract, UserContract,
        DynamicDialogBinding, Feedback, ServiceTicketFeedbackRef, Object, PollAnswer,
        ServiceTicket, GuestParkingRequest, GuestParkingSettings, AuditLog, Space, SpaceView, OtpCode,
        StorageFile, BotMessageRef, TelegramChat,
    ]
    for model in models_to_register:
        db_manager.repositories.register(model)

    services_to_register = {
        "user": UserService,
        "auth": AuthService,
        "role": RoleService,
        "permission": PermissionService,
        "contract": ContractService,
        "dynamic_dialog_binding": DynamicDialogBindingService,
        "feedback": FeedbackService,
        "service_ticket_feedback_ref": ServiceTicketFeedbackRefService,
        "object": ObjectService,
        "poll": PollService,
        "space": SpaceService,
        "service_ticket": ServiceTicketService,
        "guest_parking": GuestParkingService,
        "guest_parking_settings": GuestParkingSettingsService,
        "audit_log": AuditLogService,
        "bot_message_ref": BotMessageRefService,
        "telegram_chat": TelegramChatService,
        "space_view": SpaceViewService,
        "otp": OtpService,
        "storage_file": StorageFileService,
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


async def _ensure_rbac_defaults():
    """Ensure required system roles and permissions exist on every startup."""
    from sqlalchemy import text

    role_names = {
        EVERYONE_ROLE_CODE: "Все пользователи",
        ADMIN_ROLE_CODE: "Администратор",
        SUPER_ADMIN_ROLE_CODE: "Супер администратор",
    }
    role_permissions = {
        EVERYONE_ROLE_CODE: EVERYONE_DEFAULT_PERMISSIONS,
        ADMIN_ROLE_CODE: ADMIN_DEFAULT_PERMISSIONS,
        SUPER_ADMIN_ROLE_CODE: {item["code"] for item in DEFAULT_PERMISSIONS},
    }

    async with db_manager.get_session() as session:
        await session.execute(text("CREATE SEQUENCE IF NOT EXISTS roles_id_seq"))
        await session.execute(text("CREATE SEQUENCE IF NOT EXISTS permissions_id_seq"))
        await session.execute(text("ALTER TABLE roles ALTER COLUMN id SET DEFAULT nextval('roles_id_seq'::regclass)"))
        await session.execute(text("ALTER TABLE permissions ALTER COLUMN id SET DEFAULT nextval('permissions_id_seq'::regclass)"))
        await session.execute(text("SELECT setval('roles_id_seq', COALESCE((SELECT MAX(id) FROM roles), 0) + 1, false)"))
        await session.execute(text("SELECT setval('permissions_id_seq', COALESCE((SELECT MAX(id) FROM permissions), 0) + 1, false)"))

        for item in DEFAULT_PERMISSIONS:
            await session.execute(
                text(
                    """
                    INSERT INTO permissions (code, scope, name, description)
                    VALUES (:code, :scope, :name, :description)
                    ON CONFLICT (code) DO UPDATE
                    SET scope = EXCLUDED.scope,
                        name = EXCLUDED.name,
                        description = EXCLUDED.description,
                        updated_at = now()
                    """
                ),
                {**item, "description": item.get("description")},
            )

        for role_code, role_name in role_names.items():
            await session.execute(
                text(
                    """
                    INSERT INTO roles (code, name, is_system, is_default)
                    VALUES (:code, :name, :is_system, :is_default)
                    ON CONFLICT (code) DO UPDATE
                    SET name = EXCLUDED.name,
                        is_system = EXCLUDED.is_system,
                        is_default = EXCLUDED.is_default,
                        updated_at = now()
                    """
                ),
                {
                    "code": role_code,
                    "name": role_name,
                    "is_system": role_code in {EVERYONE_ROLE_CODE, ADMIN_ROLE_CODE, SUPER_ADMIN_ROLE_CODE},
                    "is_default": role_code == EVERYONE_ROLE_CODE,
                },
            )

        for role_code, permission_codes in role_permissions.items():
            for permission_code in sorted(permission_codes):
                await session.execute(
                    text(
                        """
                        INSERT INTO role_permissions (role_id, permission_id)
                        SELECT r.id, p.id
                        FROM roles r
                        JOIN permissions p ON p.code = :permission_code
                        WHERE r.code = :role_code
                        ON CONFLICT DO NOTHING
                        """
                    ),
                    {"role_code": role_code, "permission_code": permission_code},
                )

        await session.execute(
            text(
                """
                INSERT INTO user_roles (user_id, role_id)
                SELECT u.id, r.id
                FROM users u
                JOIN roles r ON r.code = :everyone_role_code
                ON CONFLICT DO NOTHING
                """
            ),
            {"everyone_role_code": EVERYONE_ROLE_CODE},
        )

        await session.commit()

    logger.info("RBAC defaults ensured: everyone, admin, super_admin.")


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

from shared.clients.audit_client import audit_client
from shared.clients.storage_client import storage_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Database Service (HTTP)...")
    await db_manager.initialize_db()
    _register_resources()
    try:
        audit_client.set_local_append_writer(db_manager.services.get("audit_log").append_event)
        logger.info("Audit client configured with local transactional writer.")
    except Exception as e:
        logger.warning("Audit client local writer setup failed: %s", e)
    await _ensure_default_object()
    await _ensure_rbac_defaults()
    try:
        await db_manager.services.get("guest_parking").init_reminder_cache()
    except Exception as e:
        logger.warning("Guest parking reminder cache init failed: %s", e)
    try:
        await storage_client.connect()
        logger.info("Storage client connected for cleanup.")
    except Exception as e:
        logger.warning("Storage client not available (cleanup will be skipped): %s", e)
    logger.info("Database Service ready.")
    yield
    logger.info("Shutting down Database Service...")
    audit_client.set_local_append_writer(None)
    await storage_client.disconnect()
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
