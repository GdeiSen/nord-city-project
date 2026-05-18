from datetime import datetime
from typing import Any, Optional

from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError

from database.database_manager import DatabaseManager
from models.bot_interaction_session import BotInteractionSession
from shared.utils.time_utils import now
from .base_service import BaseService, db_session_manager


ACTIVE_STATUS = "ACTIVE"
SESSION_CLOSED_STATUSES = {"CANCELLED", "COMPLETED", "EXPIRED", "FAILED"}


class BotInteractionSessionService(BaseService):
    """Durable bot workflow sessions such as service-ticket assignment input."""

    model_class = BotInteractionSession

    def __init__(self, db_manager: DatabaseManager):
        super().__init__(db_manager)

    async def _expire_stale_sessions(self, *, session, session_type: str) -> None:
        await session.execute(
            update(BotInteractionSession)
            .where(
                BotInteractionSession.session_type == session_type,
                BotInteractionSession.status == ACTIVE_STATUS,
                BotInteractionSession.expires_at.is_not(None),
                BotInteractionSession.expires_at <= now(),
            )
            .values(status="EXPIRED")
        )

    async def _get_active_by_chat(self, *, session, session_type: str, chat_id: int) -> Optional[BotInteractionSession]:
        stmt = (
            select(BotInteractionSession)
            .where(
                BotInteractionSession.session_type == session_type,
                BotInteractionSession.chat_id == int(chat_id),
                BotInteractionSession.status == ACTIVE_STATUS,
            )
            .order_by(BotInteractionSession.updated_at.desc(), BotInteractionSession.id.desc())
            .limit(1)
        )
        return (await session.execute(stmt)).scalar_one_or_none()

    async def _get_active_by_owner(
        self,
        *,
        session,
        session_type: str,
        owner_user_id: int,
    ) -> Optional[BotInteractionSession]:
        stmt = (
            select(BotInteractionSession)
            .where(
                BotInteractionSession.session_type == session_type,
                BotInteractionSession.owner_user_id == int(owner_user_id),
                BotInteractionSession.status == ACTIVE_STATUS,
            )
            .order_by(BotInteractionSession.updated_at.desc(), BotInteractionSession.id.desc())
            .limit(1)
        )
        return (await session.execute(stmt)).scalar_one_or_none()

    @db_session_manager
    async def reserve_session(
        self,
        *,
        session,
        session_type: str,
        entity_type: str,
        entity_id: int,
        chat_id: int,
        owner_user_id: int,
        prompt_message_id: Optional[int] = None,
        expires_at: Optional[datetime] = None,
        meta: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        normalized_type = str(session_type or "").strip().upper()
        await self._expire_stale_sessions(session=session, session_type=normalized_type)

        chat_session = await self._get_active_by_chat(
            session=session,
            session_type=normalized_type,
            chat_id=int(chat_id),
        )
        if chat_session is not None:
            return {"reserved": False, "reason": "chat_active", "session": chat_session}

        owner_session = await self._get_active_by_owner(
            session=session,
            session_type=normalized_type,
            owner_user_id=int(owner_user_id),
        )
        if owner_session is not None:
            return {"reserved": False, "reason": "user_active", "session": owner_session}

        created = BotInteractionSession(
            session_type=normalized_type,
            entity_type=str(entity_type or "").strip(),
            entity_id=int(entity_id),
            chat_id=int(chat_id),
            owner_user_id=int(owner_user_id),
            prompt_message_id=int(prompt_message_id) if prompt_message_id is not None else None,
            status=ACTIVE_STATUS,
            meta=meta or {},
            expires_at=expires_at,
        )
        try:
            created = await self.repository.create(session=session, obj_in=created)
            await session.flush()
            return {"reserved": True, "reason": None, "session": created}
        except IntegrityError:
            await session.rollback()
            async with self.db_manager.get_session() as retry_session:
                await self._expire_stale_sessions(session=retry_session, session_type=normalized_type)
                active = await self._get_active_by_chat(
                    session=retry_session,
                    session_type=normalized_type,
                    chat_id=int(chat_id),
                )
                reason = "chat_active"
                if active is None:
                    active = await self._get_active_by_owner(
                        session=retry_session,
                        session_type=normalized_type,
                        owner_user_id=int(owner_user_id),
                    )
                    reason = "user_active"
                await retry_session.commit()
                return {"reserved": False, "reason": reason, "session": active}

    @db_session_manager
    async def set_prompt_message(
        self,
        *,
        session,
        session_id: int,
        prompt_message_id: int,
    ) -> Optional[BotInteractionSession]:
        entity = await self.repository.get_by_id(session=session, entity_id=int(session_id))
        if entity is None or entity.status != ACTIVE_STATUS:
            return None
        entity.prompt_message_id = int(prompt_message_id)
        return await self.repository.update(session=session, obj_in=entity)

    @db_session_manager
    async def get_active_by_chat(
        self,
        *,
        session,
        session_type: str,
        chat_id: int,
    ) -> Optional[BotInteractionSession]:
        normalized_type = str(session_type or "").strip().upper()
        await self._expire_stale_sessions(session=session, session_type=normalized_type)
        return await self._get_active_by_chat(session=session, session_type=normalized_type, chat_id=int(chat_id))

    @db_session_manager
    async def close_session(
        self,
        *,
        session,
        session_id: Optional[int] = None,
        session_type: Optional[str] = None,
        chat_id: Optional[int] = None,
        owner_user_id: Optional[int] = None,
        status: str = "COMPLETED",
        meta_updates: Optional[dict[str, Any]] = None,
    ) -> Optional[BotInteractionSession]:
        normalized_status = str(status or "COMPLETED").strip().upper()
        if normalized_status not in SESSION_CLOSED_STATUSES:
            normalized_status = "COMPLETED"

        entity = None
        if session_id is not None:
            entity = await self.repository.get_by_id(session=session, entity_id=int(session_id))
        else:
            normalized_type = str(session_type or "").strip().upper()
            stmt = select(BotInteractionSession).where(BotInteractionSession.status == ACTIVE_STATUS)
            if normalized_type:
                stmt = stmt.where(BotInteractionSession.session_type == normalized_type)
            if chat_id is not None:
                stmt = stmt.where(BotInteractionSession.chat_id == int(chat_id))
            if owner_user_id is not None:
                stmt = stmt.where(BotInteractionSession.owner_user_id == int(owner_user_id))
            stmt = stmt.order_by(BotInteractionSession.updated_at.desc(), BotInteractionSession.id.desc()).limit(1)
            entity = (await session.execute(stmt)).scalar_one_or_none()

        if entity is None:
            return None
        entity.status = normalized_status
        if meta_updates:
            current_meta = dict(entity.meta or {})
            current_meta.update(meta_updates)
            entity.meta = current_meta
        return await self.repository.update(session=session, obj_in=entity)

    @db_session_manager
    async def close_active_for_owner_or_chat(
        self,
        *,
        session,
        session_type: str,
        chat_id: Optional[int] = None,
        owner_user_id: Optional[int] = None,
        status: str = "CANCELLED",
    ) -> list[BotInteractionSession]:
        normalized_type = str(session_type or "").strip().upper()
        stmt = select(BotInteractionSession).where(
            BotInteractionSession.session_type == normalized_type,
            BotInteractionSession.status == ACTIVE_STATUS,
        )
        if chat_id is not None and owner_user_id is not None:
            stmt = stmt.where(
                or_(
                    BotInteractionSession.chat_id == int(chat_id),
                    BotInteractionSession.owner_user_id == int(owner_user_id),
                )
            )
        elif chat_id is not None:
            stmt = stmt.where(BotInteractionSession.chat_id == int(chat_id))
        elif owner_user_id is not None:
            stmt = stmt.where(BotInteractionSession.owner_user_id == int(owner_user_id))
        else:
            return []

        items = list((await session.execute(stmt)).scalars().all())
        for item in items:
            item.status = str(status or "CANCELLED").strip().upper()
            await self.repository.update(session=session, obj_in=item)
        return items
