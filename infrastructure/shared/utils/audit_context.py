from __future__ import annotations

import uuid
from typing import Any, Optional

from shared.constants import AuditActorType


def generate_trace_id(prefix: str = "trace") -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def _extract_request_metadata(request: Any) -> dict[str, Any]:
    if request is None:
        return {}

    headers = getattr(request, "headers", None)
    url = getattr(request, "url", None)
    client = getattr(request, "client", None)

    method = getattr(request, "method", None)
    path = getattr(url, "path", None)
    client_ip = getattr(client, "host", None)
    user_agent = None
    if headers is not None:
        user_agent = headers.get("User-Agent")

    meta: dict[str, Any] = {}
    if method:
        meta["request_method"] = str(method)
    if path:
        meta["request_path"] = str(path)
    if client_ip:
        meta["client_ip"] = str(client_ip)
    if user_agent:
        meta["user_agent"] = str(user_agent)
    return meta


def _normalize_meta(meta: Any) -> dict[str, Any]:
    return dict(meta) if isinstance(meta, dict) else {}


def normalize_audit_context(
    audit_context: Optional[dict] = None,
    *,
    source_service: str = "web_service",
    actor_id: Any = None,
    actor_external_id: Any = None,
    actor_type: Optional[str] = None,
    actor_origin: Optional[str] = None,
    request_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    operation_id: Optional[str] = None,
    causation_id: Optional[str] = None,
    reason: Optional[str] = None,
    meta: Optional[dict] = None,
) -> dict[str, Any]:
    ctx = dict(audit_context or {})
    merged_meta = _normalize_meta(ctx.get("meta"))
    merged_meta.update(_normalize_meta(meta))

    normalized_request_id = (
        str(request_id or ctx.get("request_id") or "").strip()
        or generate_trace_id("req")
    )
    normalized_correlation_id = (
        str(correlation_id or ctx.get("correlation_id") or "").strip()
        or normalized_request_id
    )

    normalized_operation_id = (
        str(operation_id or ctx.get("operation_id") or merged_meta.get("operation_id") or "").strip()
        or normalized_correlation_id
    )
    normalized_causation_id = str(
        causation_id or ctx.get("causation_id") or merged_meta.get("causation_id") or ""
    ).strip() or None
    merged_meta["operation_id"] = normalized_operation_id
    if normalized_causation_id:
        merged_meta["causation_id"] = normalized_causation_id

    normalized_actor_id = actor_id if actor_id is not None else ctx.get("actor_id")
    normalized_actor_external_id = actor_external_id
    if normalized_actor_external_id is None:
        normalized_actor_external_id = ctx.get("actor_external_id")
    if normalized_actor_external_id is None:
        normalized_actor_external_id = merged_meta.get("actor_external_id")
    if normalized_actor_external_id is None:
        normalized_actor_external_id = merged_meta.get("telegram_user_id")
    normalized_actor_type = str(actor_type or ctx.get("actor_type") or "").upper()
    normalized_source = str(ctx.get("source") or ctx.get("source_service") or source_service or "web_service")
    normalized_reason = reason if reason is not None else ctx.get("reason")

    if not normalized_actor_type:
        if normalized_actor_id is not None:
            normalized_actor_type = AuditActorType.USER
        elif normalized_source not in {"web_service", "database_service"}:
            normalized_actor_type = AuditActorType.SERVICE
        else:
            normalized_actor_type = AuditActorType.SYSTEM

    normalized_actor_origin = str(
        actor_origin
        or ctx.get("actor_origin")
        or merged_meta.get("actor_origin")
        or ""
    ).strip()
    if not normalized_actor_origin:
        if normalized_actor_type == AuditActorType.TELEGRAM_USER:
            normalized_actor_origin = "telegram"
        elif normalized_actor_type == AuditActorType.USER:
            normalized_actor_origin = "web"
        elif normalized_actor_type == AuditActorType.SERVICE:
            normalized_actor_origin = "service"
        else:
            normalized_actor_origin = "system"
    merged_meta["actor_origin"] = normalized_actor_origin
    if normalized_actor_external_id is not None:
        merged_meta["actor_external_id"] = str(normalized_actor_external_id)

    return {
        "source": normalized_source,
        "source_service": normalized_source,
        "actor_id": normalized_actor_id,
        "actor_external_id": str(normalized_actor_external_id) if normalized_actor_external_id is not None else None,
        "actor_type": normalized_actor_type,
        "actor_origin": normalized_actor_origin,
        "request_id": normalized_request_id,
        "correlation_id": normalized_correlation_id,
        "operation_id": normalized_operation_id,
        "causation_id": normalized_causation_id,
        "reason": normalized_reason,
        "meta": merged_meta,
    }


def build_request_audit_context(
    request: Any,
    current_user: Optional[dict] = None,
    *,
    source_service: str = "web_service",
    reason: Optional[str] = None,
    meta: Optional[dict] = None,
) -> dict[str, Any]:
    headers = getattr(request, "headers", None)
    header_request_id = headers.get("X-Request-ID") if headers is not None else None
    header_correlation_id = headers.get("X-Correlation-ID") if headers is not None else None
    header_operation_id = headers.get("X-Operation-ID") if headers is not None else None
    header_causation_id = headers.get("X-Causation-ID") if headers is not None else None

    request_meta = _extract_request_metadata(request)
    merged_meta = _normalize_meta(meta)
    request_meta.update(merged_meta)
    if header_operation_id and "operation_id" not in request_meta:
        request_meta["operation_id"] = str(header_operation_id)
    if header_causation_id and "causation_id" not in request_meta:
        request_meta["causation_id"] = str(header_causation_id)

    actor_id = current_user.get("user_id") if current_user and "user_id" in current_user else None
    actor_type = AuditActorType.USER if actor_id is not None else None

    return normalize_audit_context(
        {
            "source": source_service,
            "actor_id": actor_id,
            "actor_type": actor_type,
            "request_id": header_request_id,
            "correlation_id": header_correlation_id,
            "reason": reason,
            "meta": request_meta,
        },
        source_service=source_service,
        actor_origin="web" if actor_id is not None else None,
    )


def derive_child_audit_context(
    audit_context: Optional[dict],
    *,
    source_service: Optional[str] = None,
    actor_id: Any = None,
    actor_external_id: Any = None,
    actor_type: Optional[str] = None,
    actor_origin: Optional[str] = None,
    operation_id: Optional[str] = None,
    causation_id: Optional[str] = None,
    reason: Optional[str] = None,
    meta_updates: Optional[dict] = None,
) -> dict[str, Any]:
    base_source = str(
        source_service
        or (audit_context or {}).get("source")
        or (audit_context or {}).get("source_service")
        or "web_service"
    )
    return normalize_audit_context(
        audit_context,
        source_service=base_source,
        actor_id=actor_id,
        actor_external_id=actor_external_id,
        actor_type=actor_type,
        actor_origin=actor_origin,
        operation_id=operation_id,
        causation_id=causation_id,
        reason=reason,
        meta=meta_updates,
    )
