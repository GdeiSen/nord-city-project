"""
Enrichment helpers for batch-fetching related entities.
Uses typed models (UserSummary, ObjectSummary) for enrichment.
Returns API response schemas.
"""
import json
import logging
from typing import Dict, List, Set, Any, Callable, Awaitable

from shared.clients.database_client import db_client
from shared.schemas.enrichment import ObjectSummary, ServiceTicketSummary, TelegramChatSummary, UserSummary
from api.schemas.audit_log import AuditActorResponse, AuditLogEntryResponse
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


async def batch_fetch_service_tickets(ticket_ids: Set[int]) -> Dict[int, ServiceTicketSummary]:
    """Batch-fetch service tickets by IDs. Returns {ticket_id: ServiceTicketSummary}."""
    if not ticket_ids:
        return {}
    result: Dict[int, ServiceTicketSummary] = {}
    try:
        from shared.schemas.service_ticket import ServiceTicketSchema

        resp = await db_client.service_ticket.get_by_ids(
            ids=list(ticket_ids),
            model_class=ServiceTicketSchema,
        )
        if not resp.get("success"):
            return result
        tickets = resp.get("data", []) or []
        object_ids = {
            int(ticket.object_id)
            for ticket in tickets
            if getattr(ticket, "object_id", None) is not None
        }
        object_map = await batch_fetch_objects(object_ids)
        for ticket in tickets:
            if ticket.id is None:
                continue
            object_summary = None
            if getattr(ticket, "object_id", None) is not None:
                object_summary = object_map.get(int(ticket.object_id))
            result[int(ticket.id)] = ServiceTicketSummary(
                id=int(ticket.id),
                status=ticket.status or "NEW",
                description=ticket.description or "",
                object=object_summary,
            )
    except Exception as e:
        logger.warning("Failed to batch-fetch service tickets for enrichment: %s", e)
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
    recipient_user_ids = {
        int(item.service_feedback_recipient_user_id)
        for item in items
        if getattr(item, "service_feedback_recipient_user_id", None) is not None
    }
    chat_map = await batch_fetch_telegram_chats(chat_ids)
    user_map = await batch_fetch_users(list(recipient_user_ids))
    result: List[ObjectResponse] = []
    for item in items:
        d = item.model_dump()
        admin_chat_id = d.get("admin_chat_id")
        d["admin_chat"] = chat_map.get(int(admin_chat_id)) if admin_chat_id is not None else None
        recipient_user_id = d.get("service_feedback_recipient_user_id")
        d["service_feedback_recipient_user"] = (
            user_map.get(int(recipient_user_id))
            if recipient_user_id is not None
            else None
        )
        result.append(ObjectResponse(**d))
    return result


async def enrich_feedbacks_with_users(items: List[Any]) -> List[FeedbackResponse]:
    """Enrich feedback models with user info and optional linked service ticket."""
    if not items:
        return []
    from shared.schemas.service_ticket_feedback_ref import ServiceTicketFeedbackRefSchema

    user_ids = list({f.user_id for f in items if f.user_id})
    user_map = await batch_fetch_users(user_ids)
    feedback_ids = [int(f.id) for f in items if getattr(f, "id", None) is not None]
    ref_response = await db_client.service_ticket_feedback_ref.get_by_feedback_ids(
        feedback_ids=feedback_ids,
        model_class=ServiceTicketFeedbackRefSchema,
    )
    refs = ref_response.get("data", []) if ref_response.get("success") else []
    feedback_to_ticket: Dict[int, int] = {}
    ticket_ids: Set[int] = set()
    for ref in refs or []:
        feedback_id = getattr(ref, "feedback_id", None)
        service_ticket_id = getattr(ref, "service_ticket_id", None)
        if feedback_id is None or service_ticket_id is None:
            continue
        feedback_to_ticket[int(feedback_id)] = int(service_ticket_id)
        ticket_ids.add(int(service_ticket_id))
    ticket_map = await batch_fetch_service_tickets(ticket_ids)
    result: List[FeedbackResponse] = []
    for f in items:
        d = f.model_dump()
        d["user"] = user_map.get(f.user_id, DEFAULT_USER_SUMMARY) if f.user_id else None
        service_ticket_id = feedback_to_ticket.get(int(f.id)) if getattr(f, "id", None) is not None else None
        d["service_ticket_id"] = service_ticket_id
        d["service_ticket"] = ticket_map.get(service_ticket_id) if service_ticket_id is not None else None
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


async def enrich_audit_logs_with_actor(items: List[Any]) -> List[AuditLogEntryResponse]:
    """Enrich audit log entries with normalized actor info."""
    if not items:
        return []
    actor_ids = [
        int(a.actor_id)
        for a in items
        if (
            getattr(a, "actor_id", None) is not None
            and int(a.actor_id) > 1
            and (getattr(a, "actor_type", "") or "").upper() in {"USER", "TELEGRAM_USER"}
        )
    ]
    user_map = await batch_fetch_users(actor_ids)
    result: List[AuditLogEntryResponse] = []

    def _get_user_label(user: UserSummary | None, *, fallback_id: int | None = None) -> str:
        if user is not None:
            full_name = " ".join(
                part for part in [user.last_name, user.first_name, user.middle_name] if part
            ).strip()
            if full_name:
                return full_name
            username = str(user.username or "").strip()
            if username:
                return f"@{username}"
            if user.id:
                return f"#{user.id}"
        return f"#{fallback_id}" if fallback_id is not None else "Пользователь"

    for a in items:
        d = a.model_dump()
        actor_id = int(a.actor_id) if getattr(a, "actor_id", None) is not None else None
        actor_type = (a.actor_type or "").upper()
        actor_external_id = getattr(a, "actor_external_id", None)
        meta = getattr(a, "meta", None) if isinstance(getattr(a, "meta", None), dict) else {}
        actor_snapshot = meta.get("actor_snapshot") if isinstance(meta, dict) else None
        actor: AuditActorResponse
        if isinstance(actor_snapshot, dict) and str(actor_snapshot.get("label") or "").strip():
            snapshot_user_id = actor_snapshot.get("user_id")
            snapshot_user = (
                user_map.get(int(snapshot_user_id))
                if snapshot_user_id is not None and int(snapshot_user_id) > 1
                else None
            )
            actor = AuditActorResponse(
                kind=str(actor_snapshot.get("kind") or "unknown"),
                label=str(actor_snapshot.get("label") or "").strip() or "Неизвестно",
                href=actor_snapshot.get("href"),
                user_id=int(snapshot_user_id) if snapshot_user_id is not None else None,
                user=snapshot_user,
                external_id=(
                    str(actor_snapshot.get("external_id"))
                    if actor_snapshot.get("external_id") is not None
                    else None
                ),
                actor_type=actor_snapshot.get("actor_type") or actor_type or None,
                actor_origin=actor_snapshot.get("actor_origin") or getattr(a, "actor_origin", None),
                source_service=actor_snapshot.get("source_service") or getattr(a, "source_service", None),
            )
        elif actor_id is not None and actor_id > 1 and actor_type in {"USER", "TELEGRAM_USER"}:
            user = user_map.get(actor_id)
            actor = AuditActorResponse(
                kind="user",
                label=_get_user_label(user, fallback_id=actor_id),
                href=f"/users/{actor_id}",
                user_id=actor_id,
                user=user,
                external_id=str(actor_external_id) if actor_external_id is not None else None,
                actor_type=actor_type,
                actor_origin=getattr(a, "actor_origin", None),
                source_service=getattr(a, "source_service", None),
            )
        elif actor_type == "SERVICE":
            actor = AuditActorResponse(
                kind="service",
                label=a.source_service or "Сервис",
                actor_type=actor_type,
                actor_origin=getattr(a, "actor_origin", None),
                source_service=getattr(a, "source_service", None),
            )
        elif actor_type == "TELEGRAM_USER":
            external_id = actor_external_id or actor_id
            actor = AuditActorResponse(
                kind="telegram_user",
                label=f"Telegram #{external_id}" if external_id is not None else "Telegram",
                user_id=actor_id,
                external_id=str(external_id) if external_id is not None else None,
                actor_type=actor_type,
                actor_origin=getattr(a, "actor_origin", None),
                source_service=getattr(a, "source_service", None),
            )
        elif actor_id is None or actor_id <= 1:
            actor = AuditActorResponse(
                kind="system",
                label="Система",
                actor_type=actor_type or "SYSTEM",
                actor_origin=getattr(a, "actor_origin", None),
                source_service=getattr(a, "source_service", None),
            )
        else:
            actor = AuditActorResponse(
                kind="unknown",
                label=f"#{actor_id}" if actor_id is not None else "Неизвестно",
                href=f"/users/{actor_id}" if actor_id is not None and actor_id > 1 else None,
                user_id=actor_id,
                external_id=str(actor_external_id) if actor_external_id is not None else None,
                actor_type=actor_type or None,
                actor_origin=getattr(a, "actor_origin", None),
                source_service=getattr(a, "source_service", None),
            )
        d["actor"] = actor
        d["actor_display"] = actor.label
        result.append(AuditLogEntryResponse(**d))
    return result
