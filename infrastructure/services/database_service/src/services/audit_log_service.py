"""
Audit log service for recording and querying data change history.

Acts as the persistence layer for both local transactional writes inside
database_service and remote writes from the dedicated audit_service.
"""

from datetime import datetime, timezone, timedelta
from typing import List, Optional

from sqlalchemy import delete, select

from database.database_manager import DatabaseManager
from models.audit_log import AuditLog
from shared.constants import (
    AUDIT_FIND_BY_ENTITY_DEFAULT_LIMIT,
    AUDIT_RETENTION_DAYS,
    AuditRetentionClass,
)
from .base_service import BaseService, db_session_manager

class AuditLogService(BaseService):
    """Service for audit log operations."""

    model_class = AuditLog

    def __init__(self, db_manager: DatabaseManager):
        super().__init__(db_manager)

    @db_session_manager
    async def append_event(
        self,
        *,
        session,
        entity_type: str,
        entity_id: int,
        action: str,
        event_type: str = "ENTITY_CHANGE",
        actor_id: Optional[int] = None,
        actor_type: str = "SYSTEM",
        source_service: str = "database_service",
        retention_class: str = AuditRetentionClass.OPERATIONAL,
        request_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        reason: Optional[str] = None,
        old_data: Optional[dict] = None,
        new_data: Optional[dict] = None,
        meta: Optional[dict] = None,
        audit_type: str = "fast",
    ) -> Optional[AuditLog]:
        meta_safe = meta if isinstance(meta, dict) else {}
        entry = AuditLog(
            entity_type=entity_type,
            entity_id=entity_id,
            event_type=event_type,
            action=action,
            actor_id=actor_id,
            actor_type=actor_type,
            source_service=source_service or "database_service",
            retention_class=retention_class or AuditRetentionClass.OPERATIONAL,
            request_id=request_id,
            correlation_id=correlation_id,
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
