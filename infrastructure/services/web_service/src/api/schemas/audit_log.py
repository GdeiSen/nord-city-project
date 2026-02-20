"""Response schema for audit log entries."""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, field_validator


class AuditLogEntryResponse(BaseModel):
    """Response schema for AuditLog entity."""

    id: Optional[int] = None
    entity_type: str
    entity_id: int
    action: str
    old_data: Optional[Dict[str, Any]] = None
    new_data: Optional[Dict[str, Any]] = None
    meta: Optional[Dict[str, Any]] = None
    assignee_id: Optional[int] = None
    assignee_display: Optional[str] = None  # Enriched from assignee_id
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
