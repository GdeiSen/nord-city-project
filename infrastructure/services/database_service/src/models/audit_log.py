from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Integer, JSON, Sequence, String, Index, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, Sequence("audit_log_id_seq"), primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[int] = mapped_column(BigInteger)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, server_default="ENTITY_CHANGE")
    event_category: Mapped[str] = mapped_column(String(32), nullable=False, server_default="DATA_CHANGE")
    event_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    action: Mapped[str] = mapped_column(String(16))
    actor_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    actor_external_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    actor_type: Mapped[str] = mapped_column(String(16), nullable=False, server_default="SYSTEM")
    actor_origin: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    source_service: Mapped[str] = mapped_column(String(64), nullable=False, server_default="database_service")
    retention_class: Mapped[str] = mapped_column(String(16), nullable=False, server_default="OPERATIONAL")
    request_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    correlation_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    operation_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    causation_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    old_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    new_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    meta: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    audit_type: Mapped[str] = mapped_column(String(16), nullable=False, server_default="fast")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_audit_log_entity", "entity_type", "entity_id"),
        Index("ix_audit_log_entity_created", "entity_type", "entity_id", "created_at"),
        Index("ix_audit_log_created", "created_at"),
        Index("ix_audit_log_actor_created", "actor_id", "created_at"),
        Index("ix_audit_log_correlation_created", "correlation_id", "created_at"),
        Index("ix_audit_log_operation_created", "operation_id", "created_at"),
        Index("ix_audit_log_category_created", "event_category", "created_at"),
    )
