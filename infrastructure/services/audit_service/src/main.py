import logging
import os
import signal
import sys
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
sys.path.append(project_root)

from config import get_config
from shared.clients.database_client import db_client
from shared.utils.converter import Converter

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class RPCRequest(BaseModel):
    service: str
    method: str
    params: Dict[str, Any] = {}


class RPCResponse(BaseModel):
    success: bool
    data: Any = None
    error: Optional[str] = None


class AuditRpcService:
    async def append_event(self, **params):
        response = await db_client.audit_log.append_event(**params)
        if not response.get("success"):
            raise RuntimeError(response.get("error", "Failed to append audit event"))
        return response.get("data")

    async def find_by_entity(self, **params):
        response = await db_client.audit_log.find_by_entity(**params)
        if not response.get("success"):
            raise RuntimeError(response.get("error", "Failed to fetch audit log"))
        return response.get("data")

    async def get_paginated(self, **params):
        response = await db_client.audit_log.get_paginated(**params)
        if not response.get("success"):
            raise RuntimeError(response.get("error", "Failed to fetch audit log"))
        return response.get("data")

    async def purge_before(self, **params):
        response = await db_client.audit_log.purge_before(**params)
        if not response.get("success"):
            raise RuntimeError(response.get("error", "Failed to purge audit log"))
        return response.get("data")

    async def purge_expired(self, **params):
        response = await db_client.audit_log.purge_expired(**params)
        if not response.get("success"):
            raise RuntimeError(response.get("error", "Failed to purge audit log"))
        return response.get("data")


services = {"audit": AuditRpcService()}


async def _rpc_handler(request: dict) -> dict:
    try:
        service_name = request.get("service")
        method_name = request.get("method")
        params = request.get("params", {})
        if service_name != "audit":
            return {"success": False, "error": "Unknown service"}
        service_instance = services["audit"]
        method_to_call = getattr(service_instance, method_name, None)
        if method_to_call is None:
            return {"success": False, "error": f"Method '{method_name}' not found"}
        result = await method_to_call(**params)
        return {"success": True, "data": Converter.to_dict(result)}
    except Exception as e:
        logger.error("Unhandled exception in audit RPC handler for %s: %s", request, e, exc_info=True)
        return {"success": False, "error": f"An internal server error occurred: {e}"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Audit Service (HTTP)...")
    await db_client.connect()
    logger.info("Audit Service ready.")
    yield
    logger.info("Shutting down Audit Service...")
    await db_client.disconnect()
    logger.info("Audit Service stopped.")


app = FastAPI(
    title="Nord City Audit Service (Internal)",
    description="Internal HTTP RPC endpoint for audit operations.",
    version="3.0.0",
    lifespan=lifespan,
)


@app.post("/internal/rpc", response_model=RPCResponse)
async def rpc_endpoint(request: RPCRequest):
    result = await _rpc_handler(request.model_dump())
    return result


@app.get("/health")
async def health_check():
    return {
        "status": "healthy" if db_client._connected else "degraded",
        "service": "audit_service",
        "database_client_connected": db_client._connected,
    }


def signal_handler(signum, frame):
    logger.info("Received signal %s", signum)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    config = get_config()
    host = os.getenv("AUDIT_SERVICE_HOST", config.service.host)
    port = int(os.getenv("AUDIT_SERVICE_PORT", str(config.service.port or 8005)))
    logger.info("Starting Audit Service HTTP server on %s:%s", host, port)
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        log_level=str(config.service.log_level or "info").lower(),
        reload=False,
    )
