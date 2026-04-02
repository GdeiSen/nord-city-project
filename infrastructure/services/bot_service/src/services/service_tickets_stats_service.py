import asyncio
import logging
from typing import TYPE_CHECKING, Any

from services.base_service import BaseService
from shared.schemas import BotMessageRefSchema, ObjectSchema, ObjectServiceTicketsStatsSchema
from telegram.constants import ParseMode

from utils.time_utils import now

if TYPE_CHECKING:
    from bot import Bot


logger = logging.getLogger(__name__)


class StatsService(BaseService):
    """Keeps per-object statistics messages in sync with object admin chats."""

    SYNC_INTERVAL_SECONDS = 3600

    def __init__(self, bot: "Bot"):
        super().__init__(bot)
        self._update_lock = asyncio.Lock()
        self._periodic_task: asyncio.Task[None] | None = None

    async def initialize(self) -> None:
        self.bot.managers.event.on("service_ticket_created", self._on_ticket_event)
        self.bot.managers.event.on("service_ticket_updated", self._on_ticket_event)
        self.bot.managers.event.on("service_ticket_deleted", self._on_ticket_event)
        self._periodic_task = asyncio.create_task(self._run_periodic_sync())
        await self.sync_stats_message()
        print("StatsService initialized")

    @staticmethod
    def _zero_stats(object_id: int) -> ObjectServiceTicketsStatsSchema:
        return ObjectServiceTicketsStatsSchema(
            object_id=object_id,
            total_count=0,
            new_count=0,
            in_progress_count=0,
            completed_count=0,
            new_tickets=[],
            in_progress_tickets=[],
            completed_tickets=[],
        )

    async def _run_periodic_sync(self) -> None:
        try:
            while True:
                await asyncio.sleep(self.SYNC_INTERVAL_SECONDS)
                await self.sync_stats_message()
        except asyncio.CancelledError:
            return

    async def _get_all_objects(self) -> list[ObjectSchema]:
        response = await self.bot.managers.database.object.get_all(model_class=ObjectSchema)
        if not response.get("success"):
            return []
        return response.get("data") or []

    async def _get_stats_map(self) -> dict[int, ObjectServiceTicketsStatsSchema]:
        response = await self.bot.managers.database.service_ticket.get_stats_grouped_by_object(
            model_class=ObjectServiceTicketsStatsSchema
        )
        if not response.get("success"):
            raise RuntimeError(response.get("error", "stats_grouped_query_failed"))
        stats_items = response.get("data") or []
        return {int(item.object_id): item for item in stats_items}

    async def _get_primary_message_ref(self, *, object_id: int):
        response = await self.bot.managers.database.bot_message_ref.get_primary(
            entity_type="ServiceTicketStats",
            entity_id=object_id,
            model_class=BotMessageRefSchema,
        )
        return response.get("data") if response.get("success") else None

    async def _list_known_stats_object_ids(self) -> set[int]:
        response = await self.bot.managers.database.bot_message_ref.find(
            filters={"entity_type": "ServiceTicketStats"},
            model_class=BotMessageRefSchema,
        )
        if not response.get("success"):
            return set()
        refs = response.get("data") or []
        object_ids: set[int] = set()
        for ref in refs:
            entity_id = getattr(ref, "entity_id", None)
            if entity_id is None:
                continue
            try:
                object_ids.add(int(entity_id))
            except (TypeError, ValueError):
                continue
        return object_ids

    async def _list_message_refs(self, *, object_id: int) -> list[BotMessageRefSchema]:
        response = await self.bot.managers.database.bot_message_ref.list_by_entity(
            entity_type="ServiceTicketStats",
            entity_id=object_id,
            model_class=BotMessageRefSchema,
        )
        if not response.get("success"):
            return []
        return response.get("data") or []

    async def _upsert_message_ref(self, *, object_id: int, chat_id: int, message_id: int) -> None:
        await self.bot.managers.database.bot_message_ref.upsert_message(
            entity_type="ServiceTicketStats",
            entity_id=object_id,
            chat_id=chat_id,
            message_id=message_id,
            kind="PRIMARY",
            meta={"source": "stats_service"},
            model_class=BotMessageRefSchema,
        )

    async def _delete_message_refs(self, *, object_id: int) -> None:
        await self.bot.managers.database.bot_message_ref.delete_by_entity(
            entity_type="ServiceTicketStats",
            entity_id=object_id,
        )

    async def _delete_existing_stats_messages(self, *, object_id: int) -> None:
        refs = await self._list_message_refs(object_id=object_id)
        for ref in refs:
            try:
                await self.bot.managers.message.delete_message(
                    chat_id=int(ref.chat_id),
                    message_id=int(ref.message_id),
                )
            except Exception:
                pass
        await self._delete_message_refs(object_id=object_id)

    def format_stats_message(self, object_name: str, stats: ObjectServiceTicketsStatsSchema) -> str:
        stats_no_tickets = self.bot.get_text("stats_no_tickets")
        new_tickets_str = ", ".join(map(str, stats.new_tickets)) or stats_no_tickets
        in_progress_tickets_str = ", ".join(map(str, stats.in_progress_tickets)) or stats_no_tickets
        updated_at = now().strftime("%d.%m.%Y %H:%M")
        body = self.bot.get_text(
            "stats_message",
            [
                stats.new_count,
                stats.in_progress_count,
                new_tickets_str,
                in_progress_tickets_str,
                updated_at,
            ],
        )
        return f"<b>{object_name}</b>\n\n{body}"

    async def _create_stats_message(self, *, object_id: int, chat_id: int, text: str) -> bool:
        try:
            message = await self.bot.application.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=ParseMode.HTML,
            )
            try:
                await self.bot.application.bot.pin_chat_message(
                    chat_id=chat_id,
                    message_id=message.message_id,
                    disable_notification=True,
                )
            except Exception:
                pass
            await self._upsert_message_ref(
                object_id=object_id,
                chat_id=chat_id,
                message_id=message.message_id,
            )
            return True
        except Exception as exc:
            logger.warning("Failed to create stats message for object_id=%s: %s", object_id, exc)
            return False

    async def _sync_object_stats_message(
        self,
        *,
        obj: ObjectSchema,
        stats: ObjectServiceTicketsStatsSchema,
    ) -> bool:
        object_id = int(obj.id)
        target_chat_id = int(obj.admin_chat_id)
        text = self.format_stats_message(obj.name or f"Объект #{object_id}", stats)
        primary_ref = await self._get_primary_message_ref(object_id=object_id)

        if primary_ref is None:
            return await self._create_stats_message(object_id=object_id, chat_id=target_chat_id, text=text)

        current_chat_id = int(primary_ref.chat_id)
        if current_chat_id != target_chat_id:
            await self._delete_existing_stats_messages(object_id=object_id)
            return await self._create_stats_message(object_id=object_id, chat_id=target_chat_id, text=text)

        result = await self.bot.managers.message.edit_message_detailed(
            chat_id=current_chat_id,
            message_id=int(primary_ref.message_id),
            text=text,
            parse_mode=ParseMode.HTML,
        )
        if result.success:
            return True

        await self._delete_existing_stats_messages(object_id=object_id)
        return await self._create_stats_message(object_id=object_id, chat_id=target_chat_id, text=text)

    async def _sync_all_objects(self) -> bool:
        objects = await self._get_all_objects()
        stats_map = await self._get_stats_map()
        updated = False
        object_ids = {
            int(obj.id)
            for obj in objects
            if getattr(obj, "id", None) is not None
        }
        known_stats_object_ids = await self._list_known_stats_object_ids()

        for orphan_object_id in sorted(known_stats_object_ids - object_ids):
            await self._delete_existing_stats_messages(object_id=orphan_object_id)

        for obj in objects:
            if obj.id is None:
                continue
            object_id = int(obj.id)
            if getattr(obj, "admin_chat_id", None) is None:
                await self._delete_existing_stats_messages(object_id=object_id)
                continue
            stats = stats_map.get(object_id) or self._zero_stats(object_id)
            synced = await self._sync_object_stats_message(obj=obj, stats=stats)
            updated = updated or synced

        return updated

    async def _on_ticket_event(self, _: Any) -> None:
        await self.sync_stats_message()

    async def sync_stats_message(self) -> dict[str, Any]:
        async with self._update_lock:
            updated = await self._sync_all_objects()
            return {"success": True, "data": {"updated": updated}, "error": None}

    async def recreate_stats_message(self) -> bool:
        async with self._update_lock:
            objects = await self._get_all_objects()
            for obj in objects:
                if obj.id is None:
                    continue
                await self._delete_existing_stats_messages(object_id=int(obj.id))
            return await self._sync_all_objects()
