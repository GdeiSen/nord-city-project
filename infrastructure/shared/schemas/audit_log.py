from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, field_validator


class AuditLogSchema(BaseModel):
    """Pydantic schema for AuditLog entity. Mirrors ORM."""

    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    entity_type: str = ""
    entity_id: int = 0
    event_type: str = "ENTITY_CHANGE"
    event_category: str = "DATA_CHANGE"
    event_name: Optional[str] = None
    action: str = ""
    actor_id: Optional[int] = None
    actor_external_id: Optional[str] = None
    actor_type: str = "SYSTEM"
    actor_origin: Optional[str] = None
    source_service: str = "database_service"
    retention_class: str = "OPERATIONAL"
    request_id: Optional[str] = None
    correlation_id: Optional[str] = None
    operation_id: Optional[str] = None
    causation_id: Optional[str] = None
    reason: Optional[str] = None
    old_data: Optional[Dict[str, Any]] = None
    new_data: Optional[Dict[str, Any]] = None
    meta: Optional[Dict[str, Any]] = None
    audit_type: str = "fast"
    created_at: Optional[datetime] = None

    @field_validator("meta", mode="before")
    @classmethod
    def normalize_meta(cls, v: Any) -> Optional[Dict[str, Any]]:
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
