"""
Enrichment helpers for batch-fetching related entities.
Uses typed models (UserSummary, ObjectSummary) for enrichment.
Returns API response schemas.
"""
import json
import logging
from typing import Dict, List, Set, Any, Callable, Awaitable

from shared.clients.database_client import db_client
from shared.schemas.enrichment import ObjectSummary, TelegramChatSummary, UserSummary
from api.schemas.audit_log import AuditLogEntryResponse
from api.schemas.feedbacks import FeedbackResponse
from api.schemas.guest_parking import GuestParkingResponse
from api.schemas.rental_objects import ObjectResponse
from api.schemas.service_tickets import ServiceTicketResponse
from api.schemas.users import UserResponse

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


def _extract_ticket_attachment_urls(meta_value: Any, image_value: Any) -> list[str]:
    attachments: list[str] = []
    image_candidate = str(image_value or "").strip()
    if image_candidate:
        attachments.append(image_candidate)

    meta_dict: dict[str, Any] = {}
    if isinstance(meta_value, str) and meta_value.strip():
        try:
            meta_dict = json.loads(meta_value)
        except (TypeError, ValueError):
            meta_dict = {}
    elif isinstance(meta_value, dict):
        meta_dict = meta_value

    raw_attachments = meta_dict.get("attachments") if isinstance(meta_dict, dict) else []
    if isinstance(raw_attachments, list):
        for item in raw_attachments:
            candidate = str(item or "").strip()
            if candidate and candidate not in attachments:
                attachments.append(candidate)
    return attachments


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


async def batch_fetch_telegram_chats(chat_ids: Set[int]) -> Dict[int, TelegramChatSummary]:
    """Batch-fetch Telegram chats by IDs. Returns {chat_id: TelegramChatSummary}."""
    if not chat_ids:
        return {}
    result: Dict[int, TelegramChatSummary] = {}
    try:
        from shared.schemas.telegram_chat import TelegramChatSchema

        resp = await db_client.telegram_chat.get_by_chat_ids(
            chat_ids=list(chat_ids),
            model_class=TelegramChatSchema,
        )
        if not resp.get("success"):
            return result
        for chat in resp.get("data", []):
            result[int(chat.chat_id)] = TelegramChatSummary(
                chat_id=int(chat.chat_id),
                title=chat.title or "",
                chat_type=chat.chat_type or "group",
                is_active=bool(chat.is_active),
                bot_status=chat.bot_status,
            )
    except Exception as e:
        logger.warning("Failed to batch-fetch telegram chats for enrichment: %s", e)
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


async def enrich_objects_with_chats(items: List[Any]) -> List[ObjectResponse]:
    """Enrich object models with linked Telegram chat info."""
    if not items:
        return []
    chat_ids = {
        int(item.admin_chat_id)
        for item in items
        if getattr(item, "admin_chat_id", None) is not None
    }
    chat_map = await batch_fetch_telegram_chats(chat_ids)
    result: List[ObjectResponse] = []
    for item in items:
        d = item.model_dump()
        admin_chat_id = d.get("admin_chat_id")
        d["admin_chat"] = chat_map.get(int(admin_chat_id)) if admin_chat_id is not None else None
        result.append(ObjectResponse(**d))
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
        d["attachment_urls"] = _extract_ticket_attachment_urls(t.meta, t.image)
        result.append(ServiceTicketResponse(**d))
    return result


async def enrich_audit_log_with_assignees(items: List[Any]) -> List[AuditLogEntryResponse]:
    """Enrich audit log entries with actor display name. Returns list of AuditLogEntryResponse."""
    if not items:
        return []
    actor_ids = [
        a.actor_id
        for a in items
        if (
            getattr(a, "actor_id", None) is not None
            and a.actor_id > 1
            and (getattr(a, "actor_type", "") or "").upper() == "USER"
        )
    ]
    user_map = await batch_fetch_users(actor_ids)
    result: List[AuditLogEntryResponse] = []
    for a in items:
        d = a.model_dump()
        actor_id = a.actor_id
        actor_type = (a.actor_type or "").upper()
        if actor_type == "SERVICE":
            d["actor_display"] = a.source_service or "Сервис"
        elif actor_type == "TELEGRAM_USER":
            external_id = getattr(a, "actor_external_id", None) or actor_id
            d["actor_display"] = f"Telegram #{external_id}" if external_id is not None else "Telegram"
        elif actor_id is None or actor_id <= 1:
            d["actor_display"] = "Система"
        elif actor_id in user_map:
            u = user_map[actor_id]
            parts = [u.last_name, u.first_name]
            name = " ".join(p or "" for p in parts).strip()
            un = u.username or ""
            d["actor_display"] = f"{name} @{un}".strip(" @") if (name or un) else f"#{actor_id}"
        else:
            d["actor_display"] = f"#{actor_id}"
        result.append(AuditLogEntryResponse(**d))
    return result
