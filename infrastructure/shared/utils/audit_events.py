from __future__ import annotations

import re
from typing import Any, Optional

from shared.clients.audit_client import audit_client
from shared.constants import AuditEventCategory, AuditRetentionClass
from shared.utils.audit_context import normalize_audit_context


_FIRST_CAP_RE = re.compile("(.)([A-Z][a-z]+)")
_ALL_CAP_RE = re.compile("([a-z0-9])([A-Z])")


def _to_snake_case(value: str) -> str:
    step1 = _FIRST_CAP_RE.sub(r"\1_\2", value or "")
    return _ALL_CAP_RE.sub(r"\1_\2", step1).lower()


def infer_audit_event_category(event_type: str) -> str:
    normalized = str(event_type or "").upper()
    if normalized.startswith("DELIVERY_"):
        return AuditEventCategory.DELIVERY_EVENT
    if normalized in {"ENTITY_CHANGE", "STATE_CHANGE"}:
        return AuditEventCategory.DATA_CHANGE
    return AuditEventCategory.BUSINESS_EVENT


async def append_business_audit_event(
    *,
    entity_type: str,
    entity_id: int,
    event_type: str,
    action: str,
    source_service: str,
    audit_context: Optional[dict] = None,
    event_name: Optional[str] = None,
    event_category: Optional[str] = None,
    reason: Optional[str] = None,
    old_data: Optional[dict] = None,
    new_data: Optional[dict] = None,
    meta: Optional[dict] = None,
    retention_class: str = AuditRetentionClass.OPERATIONAL,
    audit_type: str = "smart",
    session: Any = None,
    model_class: Any = None,
) -> dict[str, Any]:
    ctx = normalize_audit_context(
        audit_context,
        source_service=source_service,
        reason=reason,
        meta=meta,
    )
    return await audit_client.append_event(
        session=session,
        entity_type=entity_type,
        entity_id=int(entity_id),
        event_type=event_type,
        event_category=event_category or infer_audit_event_category(event_type),
        event_name=event_name or f"{_to_snake_case(entity_type)}.{str(event_type or 'event').lower()}",
        action=action,
        actor_id=ctx.get("actor_id"),
        actor_external_id=ctx.get("actor_external_id"),
        actor_type=ctx.get("actor_type", "SYSTEM"),
        actor_origin=ctx.get("actor_origin"),
        source_service=ctx.get("source_service") or source_service,
        retention_class=retention_class,
        request_id=ctx.get("request_id"),
        correlation_id=ctx.get("correlation_id"),
        operation_id=ctx.get("operation_id"),
        causation_id=ctx.get("causation_id"),
        reason=ctx.get("reason"),
        old_data=old_data,
        new_data=new_data,
        meta=ctx.get("meta") or {},
        audit_type=audit_type,
        model_class=model_class,
    )
