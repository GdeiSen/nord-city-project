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
    Paginates through /objects when needed (object service has no batch-by-ids).
    """
    if not object_ids:
        return {}
    result: Dict[int, dict] = {}
    page, page_size = 1, 100
    try:
        while object_ids - result.keys():
            resp = await db_client.object.get_paginated(
                page=page,
                page_size=page_size,
            )
            if not resp.get("success"):
                break
            data = resp.get("data", {})
            objs = data.get("items", [])
            if not objs:
                break
            for obj in objs:
                oid = obj.get("id")
                if oid in object_ids and oid not in result:
                    result[oid] = {
                        "id": oid,
                        "name": obj.get("name") or (f"БЦ-{oid}" if oid else ""),
                    }
            total = data.get("total", 0)
            if page * page_size >= total:
                break
            page += 1
    except Exception as e:
        logger.warning("Failed to batch-fetch objects for enrichment: %s", e)
    return result


async def batch_fetch_users(user_ids: List[int]) -> Dict[int, dict]:
    """
    Batch-fetch users by IDs. Returns {user_id: user_dict}.
    Uses get_by_id per user (user service has no batch-by-ids).
    """
    if not user_ids:
        return {}
    result: Dict[int, dict] = {}
    seen = set(user_ids)
    for uid in seen:
        try:
            ur = await db_client.user.get_by_id(entity_id=uid)
            if ur.get("success") and ur.get("data"):
                result[uid] = ur["data"]
        except Exception:
            pass
    return result


