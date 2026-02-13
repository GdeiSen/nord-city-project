"""
DatabaseClient -- typed proxy for database_service over HTTP.

Uses HttpRpcClient under the hood. Provides explicit service proxies
(db_client.user, db_client.service_ticket, etc.) with typed method
signatures so that callers know exactly what they can invoke.
"""

import os
import logging
from typing import Dict, Any, Optional

from shared.clients.http_rpc_client import HttpRpcClient
from shared.utils.converter import Converter

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Service proxy with explicit methods
# ---------------------------------------------------------------------------

class _CRUDProxy:
    """
    Base proxy that exposes standard CRUD operations for a service.
    Subclasses may add custom methods (find, get_stats, etc.).

    All methods accept an optional ``model_class`` keyword argument for
    backward compatibility with callers that used the old RabbitMQ-based
    client.  The argument is **ignored** — database_service determines the
    model class from the service name automatically.
    """

    def __init__(self, client: HttpRpcClient, service_name: str):
        self._client = client
        self._service = service_name

    async def _call(self, method: str, *, _model_class: Any = None, **params) -> Dict[str, Any]:
        """Execute an RPC call and optionally deserialise ``data``.

        Parameters
        ----------
        method : str
            Remote method name.
        _model_class : type, optional
            If provided, ``result["data"]`` will be converted from a raw
            dict (or list of dicts) into instances of this class via
            ``Converter.from_dict``.  This restores the behaviour callers
            relied on in the old RabbitMQ-based client.
        **params
            Keyword arguments forwarded as RPC params.
        """
        params.pop("model_class", None)
        serializable = {k: Converter.to_dict(v) for k, v in params.items()}
        result = await self._client.call(self._service, method, serializable)

        # --- Client-side deserialisation ---
        if _model_class is not None and result.get("success") and result.get("data") is not None:
            data = result["data"]
            if isinstance(data, list):
                result["data"] = [
                    Converter.from_dict(_model_class, item) if isinstance(item, dict) else item
                    for item in data
                ]
            elif isinstance(data, dict):
                result["data"] = Converter.from_dict(_model_class, data)

        return result

    # --- Standard CRUD ---

    async def create(
        self,
        *,
        model_data: Optional[dict] = None,
        model_instance: Any = None,
        model_class: Any = None,
    ) -> Dict[str, Any]:
        """Create an entity.  Accepts either ``model_data`` (dict) or
        ``model_instance`` (ORM / Pydantic object, auto-converted via
        Converter)."""
        if model_instance is not None:
            model_data = Converter.to_dict(model_instance)
        if model_data is None:
            raise ValueError("Either model_data or model_instance must be provided.")
        return await self._call("create", _model_class=model_class, model_data=model_data)

    async def get_by_id(self, *, entity_id: Any, model_class: Any = None) -> Dict[str, Any]:
        return await self._call("get_by_id", _model_class=model_class, entity_id=entity_id)

    async def get_all(self, *, model_class: Any = None) -> Dict[str, Any]:
        return await self._call("get_all", _model_class=model_class)

    async def update(
        self,
        *,
        entity_id: Any,
        update_data: dict,
        model_class: Any = None,
    ) -> Dict[str, Any]:
        return await self._call("update", _model_class=model_class, entity_id=entity_id, update_data=update_data)

    async def delete(self, *, entity_id: Any, model_class: Any = None) -> Dict[str, Any]:
        return await self._call("delete", _model_class=model_class, entity_id=entity_id)

    async def find(self, *, filters: dict, model_class: Any = None) -> Dict[str, Any]:
        return await self._call("find", _model_class=model_class, filters=filters)


class _ServiceTicketProxy(_CRUDProxy):
    """Service ticket proxy with additional methods."""

    async def get_stats(self, *, model_class: Any = None) -> Dict[str, Any]:
        return await self._call("get_stats", _model_class=model_class)

    async def get_by_msid(self, *, msid: Any, model_class: Any = None) -> Dict[str, Any]:
        return await self._call("get_by_msid", _model_class=model_class, msid=msid)


class _SpaceProxy(_CRUDProxy):
    """Space proxy with ``get_by_object_id``."""

    async def get_by_object_id(self, *, entity_id: Any, model_class: Any = None) -> Dict[str, Any]:
        return await self._call("get_by_object_id", _model_class=model_class, entity_id=entity_id)


class _OtpProxy(_CRUDProxy):
    """OTP code proxy with verification and invalidation methods."""

    async def verify_code(self, *, user_id: int, code: str, model_class: Any = None) -> Dict[str, Any]:
        return await self._call("verify_code", _model_class=model_class, user_id=user_id, code=code)

    async def invalidate_user_codes(self, *, user_id: int, model_class: Any = None) -> Dict[str, Any]:
        return await self._call("invalidate_user_codes", _model_class=model_class, user_id=user_id)


# ---------------------------------------------------------------------------
# Main client
# ---------------------------------------------------------------------------

class DatabaseClient:
    """
    Singleton client for database_service.
    Connects via HTTP (HttpRpcClient) and exposes typed service proxies.
    """

    _instance: Optional["DatabaseClient"] = None
    _is_initialized: bool = False

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._is_initialized:
            return

        base_url = os.getenv("DATABASE_SERVICE_HTTP_URL", "http://127.0.0.1:8001")
        timeout = float(os.getenv("DATABASE_SERVICE_TIMEOUT", "30"))

        self._http = HttpRpcClient(base_url, timeout=timeout)
        self._connected = False

        # --- Explicit service proxies ---
        self.user = _CRUDProxy(self._http, "user")
        self.auth = _CRUDProxy(self._http, "auth")
        self.feedback = _CRUDProxy(self._http, "feedback")
        self.object = _CRUDProxy(self._http, "object")
        self.poll = _CRUDProxy(self._http, "poll")
        self.service_ticket = _ServiceTicketProxy(self._http, "service_ticket")
        self.service_ticket_log = _CRUDProxy(self._http, "service_ticket_log")
        self.space = _SpaceProxy(self._http, "space")
        self.space_view = _CRUDProxy(self._http, "space_view")
        self.otp = _OtpProxy(self._http, "otp")

        self._is_initialized = True

    async def connect(self):
        """Open the HTTP connection to database_service."""
        if self._connected:
            return
        try:
            await self._http.connect()
            self._connected = True
            logger.info("DatabaseClient connected to database_service via HTTP.")
        except Exception as e:
            logger.error(f"Failed to connect DatabaseClient: {e}", exc_info=True)
            self._connected = False
            raise

    async def disconnect(self):
        """Close the HTTP connection."""
        if self._connected:
            await self._http.disconnect()
            self._connected = False
            logger.info("DatabaseClient disconnected.")


# Singleton instance for easy import
db_client = DatabaseClient()
