"""
Enrichment helpers for batch-fetching related entities.
Uses typed models (UserSummary, ObjectSummary) for enrichment.
Returns API response schemas.
"""
import logging
from typing import Dict, List, Set, Any, Callable, Awaitable

from shared.clients.database_client import db_client
from shared.schemas.enrichment import ObjectSummary, UserSummary
from api.schemas.service_tickets import ServiceTicketResponse
from api.schemas.feedbacks import FeedbackResponse
from api.schemas.guest_parking import GuestParkingResponse
from api.schemas.users import UserResponse
from api.schemas.audit_log import AuditLogEntryResponse

logger = logging.getLogger(__name__)

# Type for enricher: receives items (list of models), returns list of response schemas
Enricher = Callable[[List[Any]], Awaitable[List[Any]]]

DEFAULT_USER_SUMMARY = UserSummary(
    id=0,
    first_name="Unknown",
    last_name="",
    middle_name="",
    username="",
    object_id=None,
)


# --- Batch fetch (return typed models) ---


async def batch_fetch_objects(object_ids: Set[int]) -> Dict[int, ObjectSummary]:
    """Batch-fetch rental objects by IDs. Returns {object_id: ObjectSummary}."""
    if not object_ids:
        return {}
    result: Dict[int, ObjectSummary] = {}
    try:
        from shared.schemas.object import ObjectSchema

        resp = await db_client.object.get_by_ids(ids=list(object_ids), model_class=ObjectSchema)
        if not resp.get("success"):
            return result
        for obj in resp.get("data", []):
            if obj.id is not None:
                result[obj.id] = ObjectSummary(id=obj.id, name=obj.name or f"БЦ-{obj.id}")
    except Exception as e:
        logger.warning("Failed to batch-fetch objects for enrichment: %s", e)
    return result


async def batch_fetch_users(user_ids: List[int]) -> Dict[int, UserSummary]:
    """Batch-fetch users by IDs. Returns {user_id: UserSummary}."""
    if not user_ids:
        return {}
    result: Dict[int, UserSummary] = {}
    try:
        from shared.schemas.user import UserSchema

        resp = await db_client.user.get_by_ids(ids=user_ids, model_class=UserSchema)
        if not resp.get("success"):
            return result
        for u in resp.get("data", []):
            if u.id is not None:
                result[u.id] = UserSummary(
                    id=u.id,
                    first_name=u.first_name or "",
                    last_name=u.last_name or "",
                    middle_name=u.middle_name or "",
                    username=u.username or "",
                    object_id=u.object_id,
                )
    except Exception as e:
        logger.warning("Failed to batch-fetch users for enrichment: %s", e)
    return result


# --- Entity enrichers (model -> response schema) ---


async def enrich_users_with_objects(items: List[Any]) -> List[UserResponse]:
    """Enrich user models with object info. Returns list of UserResponse."""
    if not items:
        return []
    object_ids = {u.object_id for u in items if u.object_id is not None}
    object_map = await batch_fetch_objects(object_ids)
    result: List[UserResponse] = []
    for u in items:
        d = u.model_dump()
        d["object"] = object_map.get(u.object_id) if u.object_id else None
        result.append(UserResponse(**d))
    return result


async def enrich_feedbacks_with_users(items: List[Any]) -> List[FeedbackResponse]:
    """Enrich feedback models with user info. Returns list of FeedbackResponse."""
    if not items:
        return []
    user_ids = list({f.user_id for f in items if f.user_id})
    user_map = await batch_fetch_users(user_ids)
    result: List[FeedbackResponse] = []
    for f in items:
        d = f.model_dump()
        d["user"] = user_map.get(f.user_id, DEFAULT_USER_SUMMARY) if f.user_id else None
        result.append(FeedbackResponse(**d))
    return result


async def enrich_guest_parking_with_users(items: List[Any]) -> List[GuestParkingResponse]:
    """Enrich guest parking models with user info. Returns list of GuestParkingResponse."""
    if not items:
        return []
    user_ids = list({r.user_id for r in items if r.user_id})
    user_map = await batch_fetch_users(user_ids)
    result: List[GuestParkingResponse] = []
    for r in items:
        d = r.model_dump()
        d["user"] = user_map.get(r.user_id, DEFAULT_USER_SUMMARY) if r.user_id else None
        result.append(GuestParkingResponse(**d))
    return result


async def enrich_service_tickets_with_users_and_objects(
    items: List[Any],
) -> List[ServiceTicketResponse]:
    """Enrich service ticket models with user and object. Returns list of ServiceTicketResponse."""
    if not items:
        return []
    user_ids = list({t.user_id for t in items if t.user_id})
    user_map = await batch_fetch_users(user_ids)
    object_ids: Set[int] = set()
    for t in items:
        if t.object_id:
            object_ids.add(t.object_id)
        elif t.user_id:
            u = user_map.get(t.user_id)
            if u and u.object_id is not None:
                object_ids.add(u.object_id)
    object_map = await batch_fetch_objects(object_ids)
    result: List[ServiceTicketResponse] = []
    for t in items:
        d = t.model_dump()
        d["user"] = user_map.get(t.user_id, DEFAULT_USER_SUMMARY) if t.user_id else None
        oid = t.object_id or (d["user"].object_id if d.get("user") else None)
        d["object"] = object_map.get(oid) if oid else None
        result.append(ServiceTicketResponse(**d))
    return result


async def enrich_audit_log_with_assignees(items: List[Any]) -> List[AuditLogEntryResponse]:
    """Enrich audit log entries with assignee display name. Returns list of AuditLogEntryResponse."""
    if not items:
        return []
    assignee_ids = [a.assignee_id for a in items if a.assignee_id is not None and a.assignee_id > 1]
    user_map = await batch_fetch_users(assignee_ids)
    result: List[AuditLogEntryResponse] = []
    for a in items:
        d = a.model_dump()
        aid = a.assignee_id
        if aid is None or aid <= 1:
            d["assignee_display"] = "Система"
        elif aid in user_map:
            u = user_map[aid]
            parts = [u.last_name, u.first_name]
            name = " ".join(p or "" for p in parts).strip()
            un = u.username or ""
            d["assignee_display"] = f"{name} @{un}".strip(" @") if (name or un) else f"#{aid}"
        else:
            d["assignee_display"] = f"#{aid}"
        result.append(AuditLogEntryResponse(**d))
    return result
