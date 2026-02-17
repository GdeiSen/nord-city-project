"""
Audit log read-only endpoints.
- GET /?entity_type=&entity_id= : history for a specific entity (used on entity detail pages)
- GET /list : paginated list of all audit entries (for audit log page)
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from shared.clients.database_client import db_client
from api.schemas.audit_log import AuditLogEntryResponse
from api.schemas.common import PaginatedResponse, parse_sort_param
from api.schemas.list_params import parse_list_params_from_query
from api.helpers.paginated_list import create_paginated_list_handler
from api.helpers.enrichment import enrich_audit_log_with_assignees

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/audit-log", tags=["Audit Log"])


@router.get("/", response_model=List[AuditLogEntryResponse])
async def get_audit_log_by_entity(
    entity_type: str = Query(..., description="Entity type, e.g. ServiceTicket, User"),
    entity_id: int = Query(..., description="Entity ID"),
):
    """Get audit entries for an entity, ordered by created_at ascending."""
    if not entity_type:
        raise HTTPException(status_code=400, detail="entity_type is required")
    response = await db_client.audit_log.find_by_entity(
        entity_type=entity_type,
        entity_id=entity_id,
    )
    if not response.get("success"):
        raise HTTPException(
            status_code=500,
            detail=response.get("error", "Failed to fetch audit log"),
        )
    return response.get("data", [])


get_audit_log_list = create_paginated_list_handler(
    db_client.audit_log,
    enricher=enrich_audit_log_with_assignees,
    entity_label="audit log",
)
router.get("/list", response_model=PaginatedResponse[AuditLogEntryResponse])(get_audit_log_list)
