from datetime import datetime, timezone
from typing import Any, List, Optional

from sqlalchemy import select

from database.database_manager import DatabaseManager
from models.telegram_chat import TelegramChat
from shared.utils.converter import Converter
from .base_service import BaseService, db_session_manager


class TelegramChatService(BaseService):
    """Registry service for Telegram group chats known to the bot."""

    model_class = TelegramChat

    def __init__(self, db_manager: DatabaseManager):
        super().__init__(db_manager)

    @staticmethod
    def _normalize_seen_at(value: Optional[datetime | str]) -> datetime:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            raw = value.strip()
            if raw:
                try:
                    return datetime.fromisoformat(raw.replace("Z", "+00:00"))
                except ValueError:
                    pass
        return datetime.now(timezone.utc)

    @staticmethod
    def _changed_fields(old_data: dict[str, Any], new_data: dict[str, Any]) -> set[str]:
        keys = set(old_data.keys()) | set(new_data.keys())
        return {key for key in keys if old_data.get(key) != new_data.get(key)}

    @db_session_manager
    async def upsert_chat(
        self,
        *,
        session,
        chat_id: int,
        title: str = "",
        chat_type: str = "group",
        is_active: bool = True,
        bot_status: Optional[str] = None,
        last_seen_at: Optional[datetime] = None,
        meta: Optional[dict[str, Any]] = None,
        **kwargs,
    ) -> TelegramChat:
        audit_context = self._get_audit_context(kwargs)
        existing = await self.repository.get_by_id(session=session, entity_id=chat_id)
        payload_meta = dict(meta or {})
        seen_at = self._normalize_seen_at(last_seen_at)

        if existing is None:
            created = TelegramChat(
                chat_id=int(chat_id),
                title=str(title or "").strip(),
                chat_type=str(chat_type or "group").strip() or "group",
                is_active=bool(is_active),
                bot_status=str(bot_status).strip() if bot_status is not None else None,
                last_seen_at=seen_at,
                meta=payload_meta,
            )
            created = await self.repository.create(session=session, obj_in=created)
            await self._write_audit(
                session,
                int(created.chat_id),
                "create",
                old_data=None,
                new_data=Converter.to_dict(created),
                audit_context=audit_context,
            )
            return created

        old_data = Converter.to_dict(existing)
        existing.title = str(title or existing.title or "").strip()
        existing.chat_type = str(chat_type or existing.chat_type or "group").strip() or "group"
        existing.is_active = bool(is_active)
        existing.bot_status = str(bot_status).strip() if bot_status is not None else existing.bot_status
        existing.last_seen_at = seen_at
        merged_meta = dict(existing.meta or {})
        merged_meta.update(payload_meta)
        existing.meta = merged_meta
        updated = await self.repository.update(session=session, obj_in=existing)
        current = updated or existing
        new_data = Converter.to_dict(current)
        changed_fields = self._changed_fields(old_data, new_data)
        if changed_fields - {"last_seen_at", "updated_at"}:
            await self._write_audit(
                session,
                int(current.chat_id),
                "update",
                old_data=old_data,
                new_data=new_data,
                audit_context=audit_context,
            )
        return current

    @db_session_manager
    async def get_known_chats(
        self,
        *,
        session,
        include_inactive: bool = False,
    ) -> List[TelegramChat]:
        stmt = select(TelegramChat).where(TelegramChat.chat_type != "private")
        if not include_inactive:
            stmt = stmt.where(TelegramChat.is_active.is_(True))
        stmt = stmt.order_by(TelegramChat.title.asc(), TelegramChat.chat_id.asc())
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @db_session_manager
    async def get_by_chat_ids(self, *, session, chat_ids: List[int]) -> List[TelegramChat]:
        normalized_ids = sorted({int(chat_id) for chat_id in chat_ids if chat_id is not None})
        if not normalized_ids:
            return []
        stmt = select(TelegramChat).where(TelegramChat.chat_id.in_(normalized_ids))
        result = await session.execute(stmt)
        return list(result.scalars().all())
