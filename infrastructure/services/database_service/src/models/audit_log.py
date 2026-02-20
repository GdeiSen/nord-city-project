from datetime import datetime
from typing import Any, Optional

from sqlalchemy import BigInteger, DateTime, Integer, JSON, Sequence, String, Index, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, Sequence("audit_log_id_seq"), primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[int] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(String(16))
    old_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    new_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    meta: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    assignee_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    audit_type: Mapped[str] = mapped_column(String(16), nullable=False, server_default="fast")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_audit_log_entity", "entity_type", "entity_id"),
        Index("ix_audit_log_entity_created", "entity_type", "entity_id", "created_at"),
    )
