"""Response schema for audit log entries."""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, field_validator
from api.schemas.enrichment import UserSummary


class AuditActorResponse(BaseModel):
    """Normalized initiator info for audit log entries."""

    kind: str
    label: str
    href: Optional[str] = None
    user_id: Optional[int] = None
    user: Optional[UserSummary] = None
    external_id: Optional[str] = None
    actor_type: Optional[str] = None
    actor_origin: Optional[str] = None
    source_service: Optional[str] = None


class AuditLogEntryResponse(BaseModel):
    """Response schema for AuditLog entity."""

    id: Optional[int] = None
    entity_type: str
    entity_id: int
    event_type: str = "ENTITY_CHANGE"
    event_category: str = "DATA_CHANGE"
    event_name: Optional[str] = None
    action: str
    actor_id: Optional[int] = None
    actor_external_id: Optional[str] = None
    actor_type: str = "SYSTEM"
    actor_origin: Optional[str] = None
    actor_display: Optional[str] = None
    actor: Optional[AuditActorResponse] = None
    source_service: Optional[str] = None
    retention_class: Optional[str] = None
    request_id: Optional[str] = None
    correlation_id: Optional[str] = None
    operation_id: Optional[str] = None
    causation_id: Optional[str] = None
    reason: Optional[str] = None
    old_data: Optional[Dict[str, Any]] = None
    new_data: Optional[Dict[str, Any]] = None
    meta: Optional[Dict[str, Any]] = None
    audit_type: Optional[str] = None  # fast, smart, heavy
    created_at: Optional[datetime] = None

    @field_validator("meta", mode="before")
    @classmethod
    def normalize_meta(cls, v: Any) -> Optional[Dict[str, Any]]:
        """Normalize meta to dict or None. DB may have invalid JSON (list, etc.)."""
        if v is None:
            return None
        if isinstance(v, dict):
            return v
        if isinstance(v, list):
            for item in reversed(v):
                if isinstance(item, dict):
                    return item
            return None
        return None
