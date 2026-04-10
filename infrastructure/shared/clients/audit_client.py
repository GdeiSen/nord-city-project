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

    @staticmethod
    def _should_fallback_to_database(error: Optional[str]) -> bool:
        text = str(error or "").lower()
        if not text:
            return False
        return any(
            marker in text
            for marker in (
                "rpc connection error",
                "all connection attempts failed",
                "connection refused",
                "failed to connect",
            )
        )

    async def _append_event_via_database_service(self, **params) -> Dict[str, Any]:
        from shared.clients.database_client import db_client

        logger.warning(
            "Falling back to database_service for audit append_event: entity=%s id=%s event_type=%s action=%s",
            params.get("entity_type"),
            params.get("entity_id"),
            params.get("event_type"),
            params.get("action"),
        )
        return await db_client.audit_log.append_event(**params)

    async def append_event(
        self,
        *,
        entity_type: str,
        entity_id: int,
        action: str,
        event_type: str = "ENTITY_CHANGE",
        event_category: Optional[str] = None,
        event_name: Optional[str] = None,
        actor_id: Optional[int] = None,
        actor_external_id: Optional[str] = None,
        actor_type: str = "SYSTEM",
        actor_origin: Optional[str] = None,
        source_service: str = "database_service",
        retention_class: str = "OPERATIONAL",
        request_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        operation_id: Optional[str] = None,
        causation_id: Optional[str] = None,
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
                event_category=event_category,
                event_name=event_name,
                action=action,
                actor_id=actor_id,
                actor_external_id=actor_external_id,
                actor_type=actor_type,
                actor_origin=actor_origin,
                source_service=source_service,
                retention_class=retention_class,
                request_id=request_id,
                correlation_id=correlation_id,
                operation_id=operation_id,
                causation_id=causation_id,
                reason=reason,
                old_data=old_data,
                new_data=new_data,
                meta=meta or {},
                audit_type=audit_type,
            )
            return {"success": True, "data": Converter.to_dict(data), "error": None}
        result = await self._call(
            "append_event",
            _model_class=model_class,
            entity_type=entity_type,
            entity_id=entity_id,
            event_type=event_type,
            event_category=event_category,
            event_name=event_name,
            action=action,
            actor_id=actor_id,
            actor_external_id=actor_external_id,
            actor_type=actor_type,
            actor_origin=actor_origin,
            source_service=source_service,
            retention_class=retention_class,
            request_id=request_id,
            correlation_id=correlation_id,
            operation_id=operation_id,
            causation_id=causation_id,
            reason=reason,
            old_data=old_data,
            new_data=new_data,
            meta=meta or {},
            audit_type=audit_type,
        )
        if result.get("success") or not self._should_fallback_to_database(result.get("error")):
            return result
        return await self._append_event_via_database_service(
            entity_type=entity_type,
            entity_id=entity_id,
            event_type=event_type,
            event_category=event_category,
            event_name=event_name,
            action=action,
            actor_id=actor_id,
            actor_external_id=actor_external_id,
            actor_type=actor_type,
            actor_origin=actor_origin,
            source_service=source_service,
            retention_class=retention_class,
            request_id=request_id,
            correlation_id=correlation_id,
            operation_id=operation_id,
            causation_id=causation_id,
            reason=reason,
            old_data=old_data,
            new_data=new_data,
            meta=meta or {},
            audit_type=audit_type,
            model_class=model_class,
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

    async def get_by_id(
        self,
        *,
        entity_id: int,
        model_class: Any = None,
    ) -> Dict[str, Any]:
        return await self._call(
            "get_by_id",
            _model_class=model_class,
            entity_id=entity_id,
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
