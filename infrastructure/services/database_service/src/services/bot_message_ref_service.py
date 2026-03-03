from typing import Any, Optional

from sqlalchemy import delete, select

from database.database_manager import DatabaseManager
from models.bot_message_ref import BotMessageRef
from .base_service import BaseService, db_session_manager


class BotMessageRefService(BaseService):
    """Stores Telegram/admin chat message references outside the audit trail."""

    model_class = BotMessageRef

    def __init__(self, db_manager: DatabaseManager):
        super().__init__(db_manager)

    @db_session_manager
    async def upsert_message(
        self,
        *,
        session,
        entity_type: str,
        entity_id: int,
        chat_id: int,
        message_id: int,
        kind: str = "PRIMARY",
        meta: Optional[dict] = None,
    ) -> BotMessageRef:
        stmt = select(BotMessageRef).where(
            BotMessageRef.chat_id == chat_id,
            BotMessageRef.message_id == message_id,
        )
        existing = (await session.execute(stmt)).scalar_one_or_none()
        if existing is None and kind == "PRIMARY":
            stmt = select(BotMessageRef).where(
                BotMessageRef.entity_type == entity_type,
                BotMessageRef.entity_id == entity_id,
                BotMessageRef.kind == kind,
            )
            existing = (await session.execute(stmt)).scalar_one_or_none()

        if existing is None:
            created = BotMessageRef(
                entity_type=entity_type,
                entity_id=entity_id,
                chat_id=chat_id,
                message_id=message_id,
                kind=kind,
                meta=meta or {},
            )
            return await self.repository.create(session=session, obj_in=created)

        existing.entity_type = entity_type
        existing.entity_id = entity_id
        existing.chat_id = chat_id
        existing.message_id = message_id
        existing.kind = kind
        existing.meta = meta or {}
        updated = await self.repository.update(session=session, obj_in=existing)
        return updated or existing

    @db_session_manager
    async def list_by_entity(
        self,
        *,
        session,
        entity_type: str,
        entity_id: int,
    ) -> list[BotMessageRef]:
        stmt = (
            select(BotMessageRef)
            .where(BotMessageRef.entity_type == entity_type, BotMessageRef.entity_id == entity_id)
            .order_by(BotMessageRef.created_at.asc(), BotMessageRef.id.asc())
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @db_session_manager
    async def get_primary(
        self,
        *,
        session,
        entity_type: str,
        entity_id: int,
    ) -> Optional[BotMessageRef]:
        stmt = (
            select(BotMessageRef)
            .where(
                BotMessageRef.entity_type == entity_type,
                BotMessageRef.entity_id == entity_id,
                BotMessageRef.kind == "PRIMARY",
            )
            .order_by(BotMessageRef.updated_at.desc(), BotMessageRef.id.desc())
            .limit(1)
        )
        return (await session.execute(stmt)).scalar_one_or_none()

    @db_session_manager
    async def find_by_message(
        self,
        *,
        session,
        chat_id: int,
        message_id: int,
        entity_type: Optional[str] = None,
    ) -> Optional[BotMessageRef]:
        stmt = select(BotMessageRef).where(
            BotMessageRef.chat_id == chat_id,
            BotMessageRef.message_id == message_id,
        )
        if entity_type:
            stmt = stmt.where(BotMessageRef.entity_type == entity_type)
        return (await session.execute(stmt)).scalar_one_or_none()

    @db_session_manager
    async def delete_by_entity(
        self,
        *,
        session,
        entity_type: str,
        entity_id: int,
    ) -> int:
        stmt = delete(BotMessageRef).where(
            BotMessageRef.entity_type == entity_type,
            BotMessageRef.entity_id == entity_id,
        )
        result = await session.execute(stmt)
        return int(result.rowcount or 0)
