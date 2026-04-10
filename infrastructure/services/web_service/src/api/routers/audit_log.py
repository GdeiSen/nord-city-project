"""
Audit log read-only endpoints.
- GET /?entity_type=&entity_id= : history for a specific entity (used on entity detail pages)
- GET /list : paginated list of all audit entries (for audit log page)
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from shared.clients.audit_client import audit_client
from shared.constants import Roles
from shared.schemas.audit_log import AuditLogSchema
from api.schemas.audit_log import AuditLogEntryResponse
from api.schemas.common import PaginatedResponse
from api.helpers.paginated_list import create_paginated_list_handler
from api.helpers.enrichment import enrich_audit_logs_with_actor
from api.dependencies import get_current_user

router = APIRouter(prefix="/audit-log", tags=["Audit Log"])


def _require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    role = current_user.get("role")
    if role not in (Roles.ADMIN, Roles.SUPER_ADMIN):
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    return current_user


@router.get("/", response_model=List[AuditLogEntryResponse])
async def get_audit_log_by_entity(
    entity_type: str = Query(..., description="Entity type, e.g. ServiceTicket, User"),
    entity_id: int = Query(..., description="Entity ID"),
    limit: Optional[int] = Query(None, ge=0, le=2000, description="Max entries (default 500)"),
    _: dict = Depends(_require_admin),
):
    """Get audit entries for an entity, ordered by created_at ascending."""
    if not entity_type:
        raise HTTPException(status_code=400, detail="entity_type is required")
    response = await audit_client.find_by_entity(
        entity_type=entity_type,
        entity_id=entity_id,
        limit=limit,
        model_class=AuditLogSchema,
    )
    if not response.get("success"):
        raise HTTPException(
            status_code=500,
            detail=response.get("error", "Failed to fetch audit log"),
        )
    items = response.get("data", [])
    return await enrich_audit_logs_with_actor(items)


@router.get("/entries/{entry_id}", response_model=AuditLogEntryResponse)
async def get_audit_log_entry(
    entry_id: int,
    _: dict = Depends(_require_admin),
):
    response = await audit_client.get_by_id(entity_id=entry_id, model_class=AuditLogSchema)
    if not response.get("success"):
        raise HTTPException(
            status_code=404,
            detail=response.get("error", "Audit entry not found"),
        )
    item = response.get("data")
    if item is None:
        raise HTTPException(status_code=404, detail="Audit entry not found")
    enriched = await enrich_audit_logs_with_actor([item])
    if not enriched:
        raise HTTPException(status_code=404, detail="Audit entry not found")
    return enriched[0]


get_audit_log_list = create_paginated_list_handler(
    audit_client,
    model_class=AuditLogSchema,
    enricher=enrich_audit_logs_with_actor,
    entity_label="audit log",
)
router.get("/list", response_model=PaginatedResponse[AuditLogEntryResponse], dependencies=[Depends(_require_admin)])(get_audit_log_list)
