from datetime import timedelta
from typing import Any, Optional

from shared.schemas import BotInteractionSessionSchema, BotMessageRefSchema
from utils.time_utils import now
from .base_service import BaseService


ASSIGNMENT_SESSION_TYPE = "SERVICE_TICKET_ASSIGNMENT"


class BotStateService(BaseService):
    """Durable bot message and interaction state helpers."""

    async def initialize(self) -> None:
        pass

    async def upsert_message_ref(
        self,
        *,
        entity_type: str,
        entity_id: int,
        chat_id: int,
        message_id: int,
        kind: str = "PRIMARY",
        meta: Optional[dict[str, Any]] = None,
    ) -> None:
        await self.bot.managers.database.bot_message_ref.upsert_message(
            entity_type=entity_type,
            entity_id=entity_id,
            chat_id=chat_id,
            message_id=message_id,
            kind=kind,
            meta=meta or {},
            model_class=BotMessageRefSchema,
        )

    async def get_primary_message_ref(self, *, entity_type: str, entity_id: int) -> Any:
        result = await self.bot.managers.database.bot_message_ref.get_primary(
            entity_type=entity_type,
            entity_id=entity_id,
            model_class=BotMessageRefSchema,
        )
        return result.get("data") if result.get("success") else None

    async def list_message_refs(self, *, entity_type: str, entity_id: int) -> list[Any]:
        result = await self.bot.managers.database.bot_message_ref.list_by_entity(
            entity_type=entity_type,
            entity_id=entity_id,
            model_class=BotMessageRefSchema,
        )
        return result.get("data", []) if result.get("success") else []

    async def find_message_ref(
        self,
        *,
        chat_id: int,
        message_id: int,
        entity_type: Optional[str] = None,
    ) -> Any:
        result = await self.bot.managers.database.bot_message_ref.find_by_message(
            chat_id=chat_id,
            message_id=message_id,
            entity_type=entity_type,
            model_class=BotMessageRefSchema,
        )
        return result.get("data") if result.get("success") else None

    async def delete_message_refs(self, *, entity_type: str, entity_id: int) -> None:
        await self.bot.managers.database.bot_message_ref.delete_by_entity(
            entity_type=entity_type,
            entity_id=entity_id,
        )

    async def reserve_ticket_assignment(
        self,
        *,
        ticket_id: int,
        admin_chat_id: int,
        owner_user_id: int,
        timeout_seconds: int = 600,
    ) -> tuple[bool, str | None, dict[str, Any] | None]:
        response = await self.bot.managers.database.bot_interaction_session.reserve_session(
            session_type=ASSIGNMENT_SESSION_TYPE,
            entity_type="ServiceTicket",
            entity_id=int(ticket_id),
            chat_id=int(admin_chat_id),
            owner_user_id=int(owner_user_id),
            expires_at=(now() + timedelta(seconds=timeout_seconds)).isoformat(),
            meta={"source": "ticket_assignment_prompt"},
        )
        if not response.get("success"):
            return False, "error", None
        data = response.get("data") or {}
        session = data.get("session") if isinstance(data, dict) else None
        return bool(data.get("reserved")), data.get("reason"), self._session_to_dict(session)

    async def set_ticket_assignment_prompt(
        self,
        *,
        session_id: int,
        prompt_message_id: int,
    ) -> dict[str, Any] | None:
        response = await self.bot.managers.database.bot_interaction_session.set_prompt_message(
            session_id=int(session_id),
            prompt_message_id=int(prompt_message_id),
            model_class=BotInteractionSessionSchema,
        )
        if not response.get("success"):
            return None
        return self._session_to_dict(response.get("data"))

    async def get_active_ticket_assignment_by_chat(self, admin_chat_id: int | None) -> dict[str, Any] | None:
        if admin_chat_id is None:
            return None
        response = await self.bot.managers.database.bot_interaction_session.get_active_by_chat(
            session_type=ASSIGNMENT_SESSION_TYPE,
            chat_id=int(admin_chat_id),
            model_class=BotInteractionSessionSchema,
        )
        if not response.get("success"):
            return None
        return self._session_to_dict(response.get("data"))

    async def close_ticket_assignment(
        self,
        *,
        session_id: int | None = None,
        admin_chat_id: int | None = None,
        owner_user_id: int | None = None,
        status: str = "COMPLETED",
        meta_updates: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any] | None:
        response = await self.bot.managers.database.bot_interaction_session.close_session(
            session_id=session_id,
            session_type=ASSIGNMENT_SESSION_TYPE,
            chat_id=admin_chat_id,
            owner_user_id=owner_user_id,
            status=status,
            meta_updates=meta_updates or {},
            model_class=BotInteractionSessionSchema,
        )
        if not response.get("success"):
            return None
        return self._session_to_dict(response.get("data"))

    async def close_ticket_assignments_for_owner_or_chat(
        self,
        *,
        admin_chat_id: int | None = None,
        owner_user_id: int | None = None,
        status: str = "CANCELLED",
    ) -> list[dict[str, Any]]:
        response = await self.bot.managers.database.bot_interaction_session.close_active_for_owner_or_chat(
            session_type=ASSIGNMENT_SESSION_TYPE,
            chat_id=admin_chat_id,
            owner_user_id=owner_user_id,
            status=status,
            model_class=BotInteractionSessionSchema,
        )
        if not response.get("success"):
            return []
        return [self._session_to_dict(item) for item in (response.get("data") or []) if item is not None]

    @staticmethod
    def _session_to_dict(session: Any) -> dict[str, Any] | None:
        if session is None:
            return None
        if isinstance(session, dict):
            return dict(session)
        if hasattr(session, "model_dump"):
            return session.model_dump()
        return {
            "id": getattr(session, "id", None),
            "session_type": getattr(session, "session_type", None),
            "entity_type": getattr(session, "entity_type", None),
            "entity_id": getattr(session, "entity_id", None),
            "chat_id": getattr(session, "chat_id", None),
            "owner_user_id": getattr(session, "owner_user_id", None),
            "prompt_message_id": getattr(session, "prompt_message_id", None),
            "status": getattr(session, "status", None),
            "meta": getattr(session, "meta", None),
            "expires_at": getattr(session, "expires_at", None),
        }
