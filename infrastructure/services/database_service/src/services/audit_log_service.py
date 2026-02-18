"""
Audit log service for recording and querying data change history.
Supports explicit append (e.g. from bot with metadata) and find_by_entity for status history queries.
Modes: fast (no old/new), smart (diff only), heavy (full old/new).
"""

import logging
from typing import List, Optional, Dict, Any

from sqlalchemy import select

from database.database_manager import DatabaseManager
from shared.models.audit_log import AuditLog
from shared.utils.converter import Converter
from shared.utils.audit_diff import compute_smart_diff
from .base_service import BaseService, db_session_manager

logger = logging.getLogger(__name__)


# Services that should have audit logging (exclude audit_log itself, otp, auth)
AUDITED_SERVICES = {
    "user",
    "feedback",
    "object",
    "poll",
    "service_ticket",
    "space",
    "space_view",
}

# Map service name to entity_type (model name)
SERVICE_TO_ENTITY_TYPE = {
    "user": "User",
    "feedback": "Feedback",
    "object": "Object",
    "poll": "PollAnswer",
    "service_ticket": "ServiceTicket",
    "space": "Space",
    "space_view": "SpaceView",
}


class AuditLogService(BaseService):
    """Service for audit log operations."""

    model_class = AuditLog

    def __init__(self, db_manager: DatabaseManager):
        super().__init__(db_manager)

    async def append(
        self,
        *,
        session,
        entity_type: str,
        entity_id: int,
        action: str,
        old_data: Optional[dict] = None,
        new_data: Optional[dict] = None,
        meta: Optional[dict] = None,
        assignee_id: Optional[int] = None,
        audit_type: str = "fast",
    ) -> Optional[AuditLog]:
        """
        Create an audit log entry within the given session (same transaction).
        meta: source (caller service), requested_by, domain-specific. Must be dict or None.
        audit_type: fast, smart, or heavy.
        """
        meta_safe = meta if isinstance(meta, dict) else {}
        entry = AuditLog(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            old_data=old_data,
            new_data=new_data,
            meta=meta_safe,
            assignee_id=assignee_id,
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
    ) -> List[AuditLog]:
        """Get audit entries for an entity, ordered by created_at ascending."""
        stmt = (
            select(AuditLog)
            .where(AuditLog.entity_type == entity_type, AuditLog.entity_id == entity_id)
            .order_by(AuditLog.created_at.asc())
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await session.execute(stmt)
        return list(result.scalars().all())
