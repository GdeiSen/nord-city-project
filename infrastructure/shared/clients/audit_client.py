"""
AuditClient -- typed proxy for audit_service over HTTP with optional local writer.

database_service registers its local audit writer so entity mutations can append
audit rows in the same DB transaction. Other services use the HTTP audit_service.
"""

import logging
import os
from typing import Any, Awaitable, Callable, Dict, List, Optional

from shared.clients.http_rpc_client import HttpRpcClient
from shared.utils.converter import Converter

logger = logging.getLogger(__name__)

LocalAppendWriter = Callable[..., Awaitable[Any]]


class AuditClient:
    _instance: Optional["AuditClient"] = None
    _is_initialized: bool = False

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._is_initialized:
            return

        base_url = os.getenv("AUDIT_SERVICE_HTTP_URL", "http://127.0.0.1:8005")
        timeout = float(os.getenv("AUDIT_SERVICE_TIMEOUT", "30"))
        self._http = HttpRpcClient(base_url, timeout=timeout)
        self._connected = False
        self._local_append_writer: Optional[LocalAppendWriter] = None
        self._is_initialized = True

    def set_local_append_writer(self, writer: Optional[LocalAppendWriter]) -> None:
        self._local_append_writer = writer

    async def connect(self) -> None:
        if self._connected:
            return
        await self._http.connect()
        self._connected = True
        logger.info("AuditClient connected to audit_service via HTTP.")

    async def disconnect(self) -> None:
        if not self._connected:
            return
        await self._http.disconnect()
        self._connected = False
        logger.info("AuditClient disconnected.")

    async def _call(self, method: str, *, _model_class: Any = None, **params) -> Dict[str, Any]:
        serializable = {k: Converter.to_dict(v) for k, v in params.items()}
        result = await self._http.call("audit", method, serializable)
        if _model_class is not None and result.get("success") and result.get("data") is not None:
            data = result["data"]
            if isinstance(data, list):
                result["data"] = [
                    Converter.from_dict(_model_class, item) if isinstance(item, dict) else item
                    for item in data
                ]
            elif isinstance(data, dict):
                if "items" in data and "total" in data:
                    result["data"] = {
                        "items": [
                            Converter.from_dict(_model_class, item) if isinstance(item, dict) else item
                            for item in data.get("items", [])
                        ],
                        "total": data.get("total", 0),
                    }
                else:
                    result["data"] = Converter.from_dict(_model_class, data)
        return result

    async def append_event(
        self,
        *,
        entity_type: str,
        entity_id: int,
        action: str,
        event_type: str = "ENTITY_CHANGE",
        actor_id: Optional[int] = None,
        actor_type: str = "SYSTEM",
        source_service: str = "database_service",
        retention_class: str = "OPERATIONAL",
        request_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        reason: Optional[str] = None,
        old_data: Optional[dict] = None,
        new_data: Optional[dict] = None,
        meta: Optional[dict] = None,
        audit_type: str = "fast",
        session: Any = None,
        model_class: Any = None,
    ) -> Dict[str, Any]:
        if session is not None and self._local_append_writer is not None:
            data = await self._local_append_writer(
                session=session,
                entity_type=entity_type,
                entity_id=entity_id,
                event_type=event_type,
                action=action,
                actor_id=actor_id,
                actor_type=actor_type,
                source_service=source_service,
                retention_class=retention_class,
                request_id=request_id,
                correlation_id=correlation_id,
                reason=reason,
                old_data=old_data,
                new_data=new_data,
                meta=meta or {},
                audit_type=audit_type,
            )
            return {"success": True, "data": Converter.to_dict(data), "error": None}
        return await self._call(
            "append_event",
            _model_class=model_class,
            entity_type=entity_type,
            entity_id=entity_id,
            event_type=event_type,
            action=action,
            actor_id=actor_id,
            actor_type=actor_type,
            source_service=source_service,
            retention_class=retention_class,
            request_id=request_id,
            correlation_id=correlation_id,
            reason=reason,
            old_data=old_data,
            new_data=new_data,
            meta=meta or {},
            audit_type=audit_type,
        )

    async def find_by_entity(
        self,
        *,
        entity_type: str,
        entity_id: int,
        limit: Optional[int] = None,
        order: str = "asc",
        model_class: Any = None,
    ) -> Dict[str, Any]:
        return await self._call(
            "find_by_entity",
            _model_class=model_class,
            entity_type=entity_type,
            entity_id=entity_id,
            limit=limit,
            order=order,
        )

    async def get_paginated(
        self,
        *,
        page: int = 1,
        page_size: int = 10,
        sort: Optional[List[dict]] = None,
        filters: Optional[List[dict]] = None,
        search: Optional[str] = None,
        search_columns: Optional[List[str]] = None,
        model_class: Any = None,
    ) -> Dict[str, Any]:
        return await self._call(
            "get_paginated",
            _model_class=model_class,
            page=page,
            page_size=page_size,
            sort=sort or [],
            filters=filters or [],
            search=search or "",
            search_columns=search_columns or [],
        )

    async def purge_before(
        self,
        *,
        before_iso: str,
        retention_class: Optional[str] = None,
        batch_size: int = 1000,
        model_class: Any = None,
    ) -> Dict[str, Any]:
        return await self._call(
            "purge_before",
            _model_class=model_class,
            before_iso=before_iso,
            retention_class=retention_class,
            batch_size=batch_size,
        )

    async def purge_expired(
        self,
        *,
        batch_size: int = 1000,
        model_class: Any = None,
    ) -> Dict[str, Any]:
        return await self._call(
            "purge_expired",
            _model_class=model_class,
            batch_size=batch_size,
        )


audit_client = AuditClient()
