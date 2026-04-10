from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Optional

from shared.schemas import GuestParkingSchema, ObjectSchema, ServiceTicketSchema, TelegramChatSchema, UserSchema

from .base_service import BaseService

if TYPE_CHECKING:
    from bot import Bot
    from telegram import Chat, Update


class ChatRoutingService(BaseService):
    """Universal routing service for object admin chats and manager recipients."""

    def __init__(self, bot: "Bot"):
        super().__init__(bot)
        self._legacy_admin_chat_id: Optional[int] = None

    async def initialize(self) -> None:
        legacy_chat_id = self.bot.managers.headers.get("ADMIN_CHAT_ID")
        self._legacy_admin_chat_id = self._coerce_chat_id(legacy_chat_id)

    @staticmethod
    def _coerce_chat_id(value: Any) -> Optional[int]:
        try:
            if value is None:
                return None
            return int(str(value).strip())
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _is_registry_chat_type(chat_type: str | None) -> bool:
        return str(chat_type or "").lower() in {"group", "supergroup", "channel"}

    async def _upsert_known_chat(
        self,
        *,
        chat_id: int,
        title: str,
        chat_type: str,
        is_active: bool = True,
        bot_status: str | None = None,
        meta: Optional[dict[str, Any]] = None,
    ) -> None:
        if not self._is_registry_chat_type(chat_type):
            return
        audit_context = self.derive_audit_context(
            source_service="bot_service",
            reason="telegram_chat_observed",
            meta_updates={
                "chat_registry_source": "telegram_observation",
                "observed_chat_id": int(chat_id),
                "observed_chat_type": str(chat_type or "").lower(),
            },
        )
        await self.bot.managers.database.telegram_chat.upsert_chat(
            chat_id=chat_id,
            title=title,
            chat_type=chat_type,
            is_active=is_active,
            bot_status=bot_status,
            last_seen_at=datetime.now(timezone.utc).isoformat(),
            meta=meta or {},
            model_class=TelegramChatSchema,
            _audit_context=audit_context,
        )

    async def observe_chat(self, chat: "Chat | None", *, is_active: bool = True, bot_status: str | None = None) -> None:
        if chat is None:
            return
        chat_type = str(getattr(chat, "type", "") or "").lower()
        if not self._is_registry_chat_type(chat_type):
            return

        title = (
            str(getattr(chat, "title", None) or "").strip()
            or str(getattr(chat, "full_name", None) or "").strip()
            or str(getattr(chat, "username", None) or "").strip()
            or f"chat {getattr(chat, 'id', '')}"
        )
        await self._upsert_known_chat(
            chat_id=int(chat.id),
            title=title,
            chat_type=chat_type,
            is_active=is_active,
            bot_status=bot_status,
        )

    async def observe_message(self, update: "Update") -> None:
        try:
            await self.observe_chat(update.effective_chat)
        except Exception:
            return

    async def observe_chat_member_update(self, update: "Update") -> None:
        chat_member_update = getattr(update, "my_chat_member", None)
        if chat_member_update is None:
            return

        chat = getattr(chat_member_update, "chat", None)
        new_chat_member = getattr(chat_member_update, "new_chat_member", None)
        status = str(getattr(new_chat_member, "status", "") or "").lower()
        is_active = status not in {"left", "kicked"}
        await self.observe_chat(chat, is_active=is_active, bot_status=status or None)

    async def get_object_chat(self, object_id: int) -> Optional[TelegramChatSchema]:
        object_response = await self.bot.managers.database.object.get_by_id(
            entity_id=object_id,
            model_class=ObjectSchema,
        )
        if not object_response.get("success") or not object_response.get("data"):
            return None
        obj = object_response["data"]
        admin_chat_id = self._coerce_chat_id(getattr(obj, "admin_chat_id", None))
        if admin_chat_id is None:
            return None

        chat_response = await self.bot.managers.database.telegram_chat.get_by_id(
            entity_id=admin_chat_id,
            model_class=TelegramChatSchema,
        )
        if chat_response.get("success") and chat_response.get("data") is not None:
            return chat_response["data"]
        return None

    async def resolve_object_chat_id(self, object_id: int | None) -> Optional[int]:
        if object_id is not None:
            chat = await self.get_object_chat(int(object_id))
            if chat is not None:
                return int(chat.chat_id)
        return self._legacy_admin_chat_id

    async def _resolve_ticket_object_id(self, ticket: ServiceTicketSchema | None) -> Optional[int]:
        if ticket is None:
            return None
        object_id = ticket.get("object_id") if isinstance(ticket, dict) else getattr(ticket, "object_id", None)
        if object_id is not None:
            return int(object_id)
        user_id = ticket.get("user_id") if isinstance(ticket, dict) else ticket.user_id
        user = await self.bot.services.user.get_user_by_id(user_id)
        user_object_id = getattr(user, "object_id", None) if user is not None else None
        return int(user_object_id) if user_object_id is not None else None

    async def resolve_chat_for_ticket(
        self,
        *,
        ticket: ServiceTicketSchema | None = None,
        ticket_id: int | None = None,
    ) -> Optional[int]:
        target_ticket = ticket
        if target_ticket is None and ticket_id is not None:
            target_ticket = await self.bot.services.service_ticket.get_service_ticket_by_id(ticket_id)
        object_id = await self._resolve_ticket_object_id(target_ticket)
        return await self.resolve_object_chat_id(object_id)

    async def resolve_chat_for_guest_parking(
        self,
        *,
        request: GuestParkingSchema | None = None,
        req_id: int | None = None,
    ) -> Optional[int]:
        target_request = request
        if target_request is None and req_id is not None:
            response = await self.bot.managers.database.guest_parking.get_by_id(
                entity_id=req_id,
                model_class=GuestParkingSchema,
            )
            target_request = response.get("data") if response.get("success") else None

        object_id = None
        if target_request is not None:
            object_id = target_request.get("object_id") if isinstance(target_request, dict) else getattr(target_request, "object_id", None)
        if object_id is None and target_request is not None:
            user_id = target_request.get("user_id") if isinstance(target_request, dict) else target_request.user_id
            user = await self.bot.services.user.get_user_by_id(user_id)
            object_id = getattr(user, "object_id", None) if user is not None else None
        return await self.resolve_object_chat_id(int(object_id) if object_id is not None else None)

    async def is_object_admin_chat(self, chat_id: int) -> bool:
        normalized_chat_id = self._coerce_chat_id(chat_id)
        if normalized_chat_id is None:
            return False
        if self._legacy_admin_chat_id is not None and normalized_chat_id == self._legacy_admin_chat_id:
            return True
        response = await self.bot.managers.database.object.find(
            filters={"admin_chat_id": normalized_chat_id},
            model_class=ObjectSchema,
        )
        if not response.get("success"):
            return False
        return bool(response.get("data"))

    async def get_objects_with_admin_chats(self) -> list[ObjectSchema]:
        response = await self.bot.managers.database.object.get_all(model_class=ObjectSchema)
        if not response.get("success"):
            return []
        items = response.get("data") or []
        return [item for item in items if getattr(item, "admin_chat_id", None) is not None]

    async def get_manager_users_for_object(self, object_id: int | None) -> list[UserSchema]:
        if object_id is None:
            return []
        response = await self.bot.managers.database.user.get_managers_for_object(
            object_id=int(object_id),
            model_class=UserSchema,
        )
        if not response.get("success"):
            return []
        return response.get("data") or []

    async def resolve_feedback_recipient_user_ids(
        self,
        *,
        ticket: ServiceTicketSchema | None = None,
        ticket_id: int | None = None,
    ) -> list[int]:
        recipient_user_id = await self.resolve_feedback_recipient_user_id(
            ticket=ticket,
            ticket_id=ticket_id,
        )
        return [recipient_user_id] if recipient_user_id is not None else []

    async def resolve_feedback_recipient_user_id(
        self,
        *,
        ticket: ServiceTicketSchema | None = None,
        ticket_id: int | None = None,
    ) -> Optional[int]:
        target_ticket = ticket
        if target_ticket is None and ticket_id is not None:
            target_ticket = await self.bot.services.service_ticket.get_service_ticket_by_id(ticket_id)
        object_id = await self._resolve_ticket_object_id(target_ticket)
        if object_id is None:
            return None
        object_response = await self.bot.managers.database.object.get_by_id(
            entity_id=int(object_id),
            model_class=ObjectSchema,
        )
        if not object_response.get("success") or object_response.get("data") is None:
            return None
        recipient_user_id = getattr(
            object_response["data"],
            "service_feedback_recipient_user_id",
            None,
        )
        try:
            return int(recipient_user_id) if recipient_user_id is not None else None
        except (TypeError, ValueError):
            return None
