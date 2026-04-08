"""
Audit log service for recording and querying data change history.

Acts as the persistence layer for both local transactional writes inside
database_service and remote writes from the dedicated audit_service.
"""

import re
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, select

from database.database_manager import DatabaseManager
from models.audit_log import AuditLog
from models.user import User
from shared.constants import (
    AUDIT_FIND_BY_ENTITY_DEFAULT_LIMIT,
    AUDIT_RETENTION_DAYS,
    AuditActorType,
    AuditRetentionClass,
)
from shared.utils.audit_events import infer_audit_event_category
from .base_service import BaseService, db_session_manager

_FIRST_CAP_RE = re.compile(r"(.)([A-Z][a-z]+)")
_ALL_CAP_RE = re.compile(r"([a-z0-9])([A-Z])")

class AuditLogService(BaseService):
    """Service for audit log operations."""

    model_class = AuditLog

    def __init__(self, db_manager: DatabaseManager):
        super().__init__(db_manager)

    @staticmethod
    def _build_user_label(user: User | None, *, fallback_id: int | None = None) -> str:
        if user is not None:
            full_name = " ".join(
                part for part in [user.last_name, user.first_name, user.middle_name] if part
            ).strip()
            if full_name:
                return full_name
            username = str(user.username or "").strip()
            if username:
                return f"@{username}"
            if getattr(user, "id", None):
                return f"#{int(user.id)}"
        return f"#{fallback_id}" if fallback_id is not None else "Пользователь"

    async def _build_actor_snapshot(
        self,
        *,
        session,
        actor_id: Optional[int],
        actor_external_id: Optional[str],
        actor_type: str,
        actor_origin: Optional[str],
        source_service: str,
        meta: Dict[str, Any],
    ) -> Dict[str, Any]:
        existing_snapshot = meta.get("actor_snapshot")
        if isinstance(existing_snapshot, dict) and str(existing_snapshot.get("label") or "").strip():
            return existing_snapshot

        normalized_actor_type = str(actor_type or AuditActorType.SYSTEM).upper()
        fallback_external_id = (
            str(actor_external_id).strip()
            if actor_external_id is not None and str(actor_external_id).strip()
            else None
        )
        user: User | None = None
        if actor_id is not None and int(actor_id) > 0:
            try:
                user = await session.get(User, int(actor_id))
            except Exception:
                user = None

        if normalized_actor_type in {AuditActorType.USER, AuditActorType.TELEGRAM_USER} and actor_id is not None and int(actor_id) > 0:
            label = self._build_user_label(user, fallback_id=int(actor_id))
            snapshot_kind = "user" if user is not None else "telegram_user" if normalized_actor_type == AuditActorType.TELEGRAM_USER else "unknown"
            return {
                "kind": snapshot_kind,
                "label": label,
                "href": f"/users/{int(actor_id)}",
                "user_id": int(actor_id),
                "external_id": fallback_external_id,
                "actor_type": normalized_actor_type,
                "actor_origin": actor_origin,
                "source_service": source_service,
            }

        if normalized_actor_type == AuditActorType.SERVICE:
            return {
                "kind": "service",
                "label": source_service or "Сервис",
                "actor_type": normalized_actor_type,
                "actor_origin": actor_origin,
                "source_service": source_service,
            }

        if normalized_actor_type == AuditActorType.TELEGRAM_USER:
            external_id = fallback_external_id or (str(actor_id) if actor_id is not None else None)
            return {
                "kind": "telegram_user",
                "label": f"Telegram #{external_id}" if external_id is not None else "Telegram",
                "user_id": int(actor_id) if actor_id is not None else None,
                "external_id": external_id,
                "actor_type": normalized_actor_type,
                "actor_origin": actor_origin,
                "source_service": source_service,
            }

        if actor_id is None or int(actor_id) <= 1:
            return {
                "kind": "system",
                "label": "Система",
                "actor_type": normalized_actor_type or AuditActorType.SYSTEM,
                "actor_origin": actor_origin,
                "source_service": source_service,
            }

        return {
            "kind": "unknown",
            "label": f"#{int(actor_id)}",
            "href": f"/users/{int(actor_id)}",
            "user_id": int(actor_id),
            "external_id": fallback_external_id,
            "actor_type": normalized_actor_type or None,
            "actor_origin": actor_origin,
            "source_service": source_service,
        }

    @staticmethod
    def _to_snake_case(value: str) -> str:
        step1 = _FIRST_CAP_RE.sub(r"\1_\2", value or "")
        return _ALL_CAP_RE.sub(r"\1_\2", step1).lower()

    @db_session_manager
    async def append_event(
        self,
        *,
        session,
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
        retention_class: str = AuditRetentionClass.OPERATIONAL,
        request_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        operation_id: Optional[str] = None,
        causation_id: Optional[str] = None,
        reason: Optional[str] = None,
        old_data: Optional[dict] = None,
        new_data: Optional[dict] = None,
        meta: Optional[dict] = None,
        audit_type: str = "fast",
    ) -> Optional[AuditLog]:
        meta_safe = dict(meta) if isinstance(meta, dict) else {}
        normalized_actor_origin = str(actor_origin or meta_safe.get("actor_origin") or "").strip()
        if not normalized_actor_origin:
            if actor_type == AuditActorType.TELEGRAM_USER:
                normalized_actor_origin = "telegram"
            elif actor_type == AuditActorType.USER:
                normalized_actor_origin = "web"
            elif actor_type == AuditActorType.SERVICE:
                normalized_actor_origin = "service"
            else:
                normalized_actor_origin = "system"
        normalized_actor_external_id = actor_external_id
        if normalized_actor_external_id is None:
            normalized_actor_external_id = meta_safe.get("actor_external_id") or meta_safe.get("telegram_user_id")
        normalized_operation_id = (
            str(operation_id or meta_safe.get("operation_id") or correlation_id or request_id or "").strip()
            or None
        )
        normalized_causation_id = str(causation_id or meta_safe.get("causation_id") or "").strip() or None
        normalized_event_category = event_category or infer_audit_event_category(event_type)
        normalized_event_name = (
            event_name
            or f"{self._to_snake_case(entity_type)}.{str(event_type or 'event').lower()}"
        )
        meta_safe["actor_snapshot"] = await self._build_actor_snapshot(
            session=session,
            actor_id=actor_id,
            actor_external_id=(
                str(normalized_actor_external_id) if normalized_actor_external_id is not None else None
            ),
            actor_type=actor_type,
            actor_origin=normalized_actor_origin,
            source_service=source_service or "database_service",
            meta=meta_safe,
        )
        entry = AuditLog(
            entity_type=entity_type,
            entity_id=entity_id,
            event_type=event_type,
            event_category=normalized_event_category,
            event_name=normalized_event_name,
            action=action,
            actor_id=actor_id,
            actor_external_id=(
                str(normalized_actor_external_id) if normalized_actor_external_id is not None else None
            ),
            actor_type=actor_type,
            actor_origin=normalized_actor_origin,
            source_service=source_service or "database_service",
            retention_class=retention_class or AuditRetentionClass.OPERATIONAL,
            request_id=request_id,
            correlation_id=correlation_id,
            operation_id=normalized_operation_id,
            causation_id=normalized_causation_id,
            reason=reason,
            old_data=old_data,
            new_data=new_data,
            meta=meta_safe,
            audit_type=audit_type,
        )
        return await self.repository.create(session=session, obj_in=entry)

    @db_session_manager
    async def find_by_entity(
        self,
        *,
        session,
        entity_type: str,
        entity_id: int,
        limit: Optional[int] = None,
        order: str = "asc",
    ) -> List[AuditLog]:
        """
        Get audit entries for an entity.

        To avoid dropping the latest history, limited reads are selected from the
        newest side and then optionally reordered into ascending display order.
        """
        if limit == 0:
            effective_limit = None
        elif limit is not None:
            effective_limit = limit
        else:
            effective_limit = AUDIT_FIND_BY_ENTITY_DEFAULT_LIMIT

        desc_stmt = (
            select(AuditLog)
            .where(AuditLog.entity_type == entity_type, AuditLog.entity_id == entity_id)
            .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        )
        if effective_limit is not None:
            desc_stmt = desc_stmt.limit(effective_limit)
        result = await session.execute(desc_stmt)
        items = list(result.scalars().all())

        normalized_order = (order or "asc").lower()
        if normalized_order == "desc":
            return items
        items.reverse()
        return items

    @db_session_manager
    async def purge_before(
        self,
        *,
        session,
        before_iso: str,
        retention_class: Optional[str] = None,
        batch_size: int = 1000,
    ) -> int:
        cutoff = datetime.fromisoformat(before_iso.replace("Z", "+00:00"))
        stmt = (
            select(AuditLog.id)
            .where(AuditLog.created_at < cutoff)
            .order_by(AuditLog.created_at.asc(), AuditLog.id.asc())
            .limit(max(1, batch_size))
        )
        if retention_class:
            stmt = stmt.where(AuditLog.retention_class == retention_class)
        ids = list((await session.execute(stmt)).scalars().all())
        if not ids:
            return 0
        delete_stmt = delete(AuditLog).where(AuditLog.id.in_(ids))
        result = await session.execute(delete_stmt)
        return int(result.rowcount or 0)

    @db_session_manager
    async def purge_expired(
        self,
        *,
        session,
        batch_size: int = 1000,
    ) -> int:
        now_utc = datetime.now(timezone.utc)
        deleted_total = 0
        for retention_class, days in AUDIT_RETENTION_DAYS.items():
            cutoff = now_utc - timedelta(days=days)
            deleted = await self.purge_before(
                session=session,
                before_iso=cutoff.isoformat(),
                retention_class=retention_class,
                batch_size=max(1, batch_size - deleted_total),
            )
            deleted_total += deleted
            if deleted_total >= batch_size:
                break
        return deleted_total
