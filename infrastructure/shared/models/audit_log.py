"""
Universal audit log for tracking data changes across all entities.
Records create, update, delete operations with optional metadata.

assignee_id: user id, or 1 for system, or service identifier.
meta.source: service that originated the request (web_service, bot_service, etc.).
audit_type: fast (no old/new), smart (diff only), heavy (full old/new).
"""

from datetime import datetime
from typing import Optional, Any

from sqlalchemy import BigInteger, String, DateTime, func, Integer, Sequence, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class AuditLog(Base):
    """Universal audit log entry."""

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, Sequence("audit_log_id_seq"), primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(64))  # e.g. "ServiceTicket", "User", "Object"
    entity_id: Mapped[int] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(String(16))  # create, update, delete
    old_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # for update/delete
    new_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # for create/update
    meta: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # source, requested_by, domain-specific
    assignee_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)  # user id, 1=system
    audit_type: Mapped[str] = mapped_column(String(16), nullable=False, server_default="fast")  # fast, smart, heavy
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_audit_log_entity", "entity_type", "entity_id"),
        Index("ix_audit_log_entity_created", "entity_type", "entity_id", "created_at"),
    )
