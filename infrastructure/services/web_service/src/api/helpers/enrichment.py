"""
Enrichment helpers for batch-fetching related entities.
Eliminates duplicated object/user fetch logic across list endpoints.
"""
import logging
from typing import Dict, List, Set

from shared.clients.database_client import db_client

logger = logging.getLogger(__name__)


# --- Entity enrichers for paginated list handlers ---


async def enrich_users_with_objects(items: list) -> None:
    """Enrich user dicts with object info. Mutates items in place."""
    if not items:
        return
    object_ids = set(u.get("object_id") for u in items if u.get("object_id"))
    object_map = await batch_fetch_objects(object_ids)
    for u in items:
        oid = u.get("object_id")
        u["object"] = object_map.get(oid) if oid else None


async def enrich_feedbacks_with_users(items: list) -> None:
    """Enrich feedback dicts with user info. Mutates items in place."""
    if not items:
        return
    user_ids = list({f.get("user_id") for f in items if f.get("user_id")})
    user_map = await batch_fetch_users(user_ids)
    default_user = {"first_name": "", "last_name": "", "username": ""}
    for f in items:
        f["user"] = user_map.get(f.get("user_id"), default_user)


async def enrich_service_tickets_with_users_and_objects(items: list) -> None:
    """Enrich service ticket dicts with user and object info. Mutates items in place."""
    if not items:
        return
    user_ids = list({t.get("user_id") for t in items if t.get("user_id")})
    user_map = await batch_fetch_users(user_ids)
    object_ids: Set[int] = set()
    for t in items:
        oid = t.get("object_id")
        if oid:
            object_ids.add(oid)
        else:
            u = user_map.get(t.get("user_id"))
            if u and u.get("object_id"):
                object_ids.add(u["object_id"])
    object_map = await batch_fetch_objects(object_ids)
    default_user = {"first_name": "Unknown", "last_name": "", "username": ""}
    for t in items:
        t["user"] = user_map.get(t.get("user_id"), default_user)
        oid = t.get("object_id") or t["user"].get("object_id")
        t["object"] = object_map.get(oid) if oid else None


async def batch_fetch_objects(object_ids: Set[int]) -> Dict[int, dict]:
    """
    Batch-fetch rental objects by IDs. Returns {object_id: {"id": id, "name": name}}.
    """
    if not object_ids:
        return {}
    result: Dict[int, dict] = {}
    try:
        resp = await db_client.object.get_by_ids(ids=list(object_ids))
        if not resp.get("success"):
            return result
        for obj in resp.get("data", []):
            oid = obj.get("id")
            if oid is not None:
                result[oid] = {
                    "id": oid,
                    "name": obj.get("name") or (f"БЦ-{oid}" if oid else ""),
                }
    except Exception as e:
        logger.warning("Failed to batch-fetch objects for enrichment: %s", e)
    return result


async def enrich_audit_log_with_assignees(items: list) -> None:
    """Enrich audit log entries with assignee display name. Mutates items in place."""
    if not items:
        return
    assignee_ids = list({a.get("assignee_id") for a in items if a.get("assignee_id") is not None and a.get("assignee_id") > 1})
    user_map = await batch_fetch_users(assignee_ids)
    for a in items:
        aid = a.get("assignee_id")
        if aid is None or aid <= 1:
            a["assignee_display"] = "Система"
        elif aid in user_map:
            u = user_map[aid]
            parts = [u.get("last_name"), u.get("first_name")]
            name = " ".join(p or "" for p in parts).strip()
            un = u.get("username", "")
            a["assignee_display"] = f"{name} @{un}".strip(" @") if (name or un) else f"#{aid}"
        else:
            a["assignee_display"] = f"#{aid}"


async def batch_fetch_users(user_ids: List[int]) -> Dict[int, dict]:
    """
    Batch-fetch users by IDs. Returns {user_id: user_dict}.
    """
    if not user_ids:
        return {}
    result: Dict[int, dict] = {}
    try:
        resp = await db_client.user.get_by_ids(ids=user_ids)
        if not resp.get("success"):
            return result
        for u in resp.get("data", []):
            uid = u.get("id")
            if uid is not None:
                result[uid] = u
    except Exception as e:
        logger.warning("Failed to batch-fetch users for enrichment: %s", e)
    return result


