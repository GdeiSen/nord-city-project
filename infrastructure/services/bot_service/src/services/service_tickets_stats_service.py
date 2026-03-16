# ./services/stats_service.py
import asyncio
import json
import logging
import os
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional
from zoneinfo import ZoneInfo

from services.base_service import BaseService
from shared.schemas.service_tickets_stats import ServiceTicketsStatsSchema
from telegram.error import BadRequest

if TYPE_CHECKING:
    from bot import Bot


logger = logging.getLogger(__name__)


class StatsService(BaseService):
    """Service for managing ticket statistics and keeping a single stats message in sync."""

    SYNC_INTERVAL_SECONDS = 3600

    def __init__(self, bot: "Bot", json_file_path: str = "stats_data.json"):
        super().__init__(bot)
        self.json_file_path = json_file_path
        self.moscow_tz = ZoneInfo("Europe/Moscow")
        self._update_lock = asyncio.Lock()
        self._scheduled_update_task: asyncio.Task[None] | None = None
        self._scheduled_validate_message = False
        self._periodic_task: asyncio.Task[None] | None = None
        self._ensure_json_file()

    async def initialize(self) -> None:
        """Initializes the statistics service."""
        self.bot.managers.event.on("service_ticket_created", self._on_ticket_created)
        self.bot.managers.event.on("service_ticket_updated", self._on_ticket_updated)
        self.bot.managers.event.on("service_ticket_deleted", self._on_ticket_deleted)
        await self.initialize_stats_message()
        print("StatsService initialized")

    def _now(self) -> datetime:
        return datetime.now(self.moscow_tz)

    def _default_data(self) -> Dict[str, Any]:
        return {
            "stats_message": {"chat_id": None, "message_id": None, "created_at": None},
            "detailed_stats": {
                "total_count": 0,
                "new_count": 0,
                "in_progress_count": 0,
                "completed_count": 0,
                "new_tickets": [],
                "in_progress_tickets": [],
                "completed_tickets": [],
                "last_update": None,
            },
        }

    @staticmethod
    def _normalize_ticket_ids(values: Any) -> list[int]:
        normalized: list[int] = []
        for value in values or []:
            try:
                normalized.append(int(value))
            except (TypeError, ValueError):
                continue
        return sorted(normalized)

    def _normalize_stats_snapshot(self, stats: Dict[str, Any] | None) -> Dict[str, Any]:
        stats = stats or {}
        return {
            "total_count": int(stats.get("total_count", 0) or 0),
            "new_count": int(stats.get("new_count", 0) or 0),
            "in_progress_count": int(stats.get("in_progress_count", 0) or 0),
            "completed_count": int(stats.get("completed_count", 0) or 0),
            "new_tickets": self._normalize_ticket_ids(stats.get("new_tickets")),
            "in_progress_tickets": self._normalize_ticket_ids(stats.get("in_progress_tickets")),
            "completed_tickets": self._normalize_ticket_ids(stats.get("completed_tickets")),
        }

    def _ensure_json_file(self) -> None:
        if not os.path.exists(self.json_file_path):
            self._save_data(self._default_data())

    def _load_data(self) -> Dict[str, Any]:
        try:
            with open(self.json_file_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self._ensure_json_file()
            return self._load_data()

        data = self._default_data()
        data["stats_message"].update(raw_data.get("stats_message", {}))

        stored_stats = raw_data.get("detailed_stats", {})
        data["detailed_stats"] = {
            **self._normalize_stats_snapshot(stored_stats),
            "last_update": stored_stats.get("last_update"),
        }

        if data != raw_data:
            self._save_data(data)

        return data

    def _save_data(self, data: Dict[str, Any]) -> None:
        with open(self.json_file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    def save_message_info(self, chat_id: Optional[int], message_id: Optional[int]) -> None:
        """Сохраняет информацию о сообщении со статистикой."""
        data = self._load_data()
        if chat_id is None or message_id is None:
            data["stats_message"] = {"chat_id": None, "message_id": None, "created_at": None}
        else:
            data["stats_message"] = {
                "chat_id": chat_id,
                "message_id": message_id,
                "created_at": self._now().isoformat(),
            }
        self._save_data(data)

    def get_message_info(self) -> Optional[Dict[str, Any]]:
        data = self._load_data()
        msg_info = data.get("stats_message", {})
        return msg_info if msg_info.get("chat_id") and msg_info.get("message_id") else None

    def _get_stored_stats_snapshot(self, data: Dict[str, Any] | None = None) -> Dict[str, Any]:
        data = data or self._load_data()
        return self._normalize_stats_snapshot(data.get("detailed_stats"))

    def _stats_signature(self, stats: Dict[str, Any]) -> str:
        return json.dumps(self._normalize_stats_snapshot(stats), ensure_ascii=False, sort_keys=True)

    def _stats_changed(self, stats: Dict[str, Any], data: Dict[str, Any] | None = None) -> bool:
        return self._stats_signature(stats) != self._stats_signature(self._get_stored_stats_snapshot(data))

    def _persist_stats_snapshot(self, stats: Dict[str, Any], *, last_update_iso: str | None) -> None:
        data = self._load_data()
        data["detailed_stats"] = {
            **self._normalize_stats_snapshot(stats),
            "last_update": last_update_iso,
        }
        self._save_data(data)

    def update_detailed_stats(self, stats: Dict[str, Any]) -> str:
        data = self._load_data()
        current_last_update = data.get("detailed_stats", {}).get("last_update")
        stats_changed = self._stats_changed(stats, data)
        next_last_update = current_last_update
        if stats_changed or not next_last_update:
            next_last_update = self._now().isoformat()
        self._persist_stats_snapshot(stats, last_update_iso=next_last_update)
        return next_last_update

    def format_stats_message(self, stats: Dict[str, Any], *, last_update_iso: str | None = None) -> str:
        """Formats the statistics into a message string."""
        time_source = last_update_iso
        if not time_source:
            data = self._load_data()
            time_source = data.get("detailed_stats", {}).get("last_update")
        time_str = (
            datetime.fromisoformat(time_source).strftime("%d.%m.%Y %H:%M")
            if time_source
            else self._now().strftime("%d.%m.%Y %H:%M")
        )

        normalized_stats = self._normalize_stats_snapshot(stats)
        stats_no_tickets = self.bot.get_text("stats_no_tickets")
        new_tickets_str = ", ".join(map(str, normalized_stats.get("new_tickets", []))) or stats_no_tickets
        in_progress_tickets_str = (
            ", ".join(map(str, normalized_stats.get("in_progress_tickets", []))) or stats_no_tickets
        )

        return self.bot.get_text(
            "stats_message",
            [
                normalized_stats.get("new_count", 0),
                normalized_stats.get("in_progress_count", 0),
                new_tickets_str,
                in_progress_tickets_str,
                time_str,
            ],
        )

    async def _get_stats(self) -> ServiceTicketsStatsSchema:
        result = await self.bot.managers.database.service_ticket.get_stats(
            model_class=ServiceTicketsStatsSchema
        )
        if result["success"] and result["data"]:
            return result["data"]
        raise RuntimeError(f"Failed to get stats: {result.get('error')}")

    async def _create_new_stats_message(self, chat_id: str | int, message_text: str) -> bool:
        """Создает новое сообщение со статистикой без попытки принудительно удалить старое."""
        try:
            message = await self.bot.application.bot.send_message(
                chat_id=int(chat_id),
                text=message_text,
                parse_mode="HTML",
            )

            try:
                await self.bot.application.bot.pin_chat_message(
                    chat_id=int(chat_id),
                    message_id=message.message_id,
                    disable_notification=True,
                )
            except Exception:
                pass

            self.save_message_info(int(chat_id), message.message_id)
            return True
        except BadRequest as exc:
            if "chat not found" in str(exc).lower():
                logger.warning(
                    "[Stats] Admin chat not found (chat_id=%s). Ensure ADMIN_CHAT_ID is correct and the bot is in the chat.",
                    chat_id,
                )
                self.save_message_info(None, None)
                return False

            logger.exception("Error creating new stats message: %s", exc)
            return False
        except Exception as exc:  # noqa: BLE001 - centralized logging
            logger.exception("Error creating new stats message: %s", exc)
            return False

    async def _delete_old_message(self) -> bool:
        """Удаляет старое сообщение со статистикой, не теряя ссылку на него при временных ошибках."""
        message_info = self.get_message_info()
        if not message_info:
            return True

        chat_id = message_info.get("chat_id")
        message_id = message_info.get("message_id")
        if not chat_id or not message_id:
            self.save_message_info(None, None)
            return True

        result = await self.bot.managers.message.delete_message_detailed(
            chat_id=chat_id,
            message_id=message_id,
        )
        if result.success:
            self.save_message_info(None, None)
            return True

        logger.warning(
            "Stats message delete skipped: chat_id=%s message_id=%s reason=%s error=%s",
            chat_id,
            message_id,
            result.reason,
            result.error,
        )
        return False

    async def _replace_inaccessible_message(
        self,
        *,
        admin_chat_id: int,
        current_message: Dict[str, Any],
        message_text: str,
        reason: str,
    ) -> bool:
        if reason == "not_found":
            self.save_message_info(None, None)
            return await self._create_new_stats_message(admin_chat_id, message_text)

        delete_result = await self.bot.managers.message.delete_message_detailed(
            chat_id=current_message["chat_id"],
            message_id=current_message["message_id"],
        )
        if delete_result.success:
            self.save_message_info(None, None)
            return await self._create_new_stats_message(admin_chat_id, message_text)

        logger.warning(
            "Stats message replacement aborted: delete failed for chat_id=%s message_id=%s reason=%s error=%s",
            current_message["chat_id"],
            current_message["message_id"],
            delete_result.reason,
            delete_result.error,
        )
        return False

    def _schedule_update(self, *, validate_message: bool = False, delay_seconds: float = 0.0) -> None:
        self._scheduled_validate_message = self._scheduled_validate_message or validate_message
        if self._scheduled_update_task and not self._scheduled_update_task.done():
            return

        async def _runner() -> None:
            try:
                if delay_seconds > 0:
                    await asyncio.sleep(delay_seconds)
                validate = self._scheduled_validate_message
                self._scheduled_validate_message = False
                await self._update_stats_message(validate_message=validate)
            except Exception as exc:  # noqa: BLE001 - background task must not crash app
                logger.exception("Scheduled stats sync failed: %s", exc)
            finally:
                self._scheduled_update_task = None

        self._scheduled_update_task = asyncio.create_task(_runner())

    async def _update_stats_message(self, *, validate_message: bool = False) -> bool:
        """Updates the statistics message only when the underlying stats snapshot changes."""
        async with self._update_lock:
            admin_chat_id = self.bot.managers.headers.get("ADMIN_CHAT_ID")
            if not admin_chat_id:
                return False

            stats_obj = await self._get_stats()
            stats = self._normalize_stats_snapshot(stats_obj.model_dump())
            stats_changed = self._stats_changed(stats)
            last_update_iso = self.update_detailed_stats(stats)
            message_text = self.format_stats_message(stats, last_update_iso=last_update_iso)
            message_info = self.get_message_info()

            if not message_info:
                return await self._create_new_stats_message(int(admin_chat_id), message_text)

            if not stats_changed and not validate_message:
                return True

            edit_result = await self.bot.managers.message.edit_message_detailed(
                chat_id=message_info["chat_id"],
                message_id=message_info["message_id"],
                text=message_text,
                parse_mode="HTML",
            )
            if edit_result.success:
                return True

            if edit_result.reason in {"not_found", "cant_edit"}:
                return await self._replace_inaccessible_message(
                    admin_chat_id=int(admin_chat_id),
                    current_message=message_info,
                    message_text=message_text,
                    reason=edit_result.reason,
                )

            logger.warning(
                "Stats message sync skipped after transient edit failure: chat_id=%s message_id=%s reason=%s error=%s",
                message_info["chat_id"],
                message_info["message_id"],
                edit_result.reason,
                edit_result.error,
            )
            return False

    async def _periodic_message_check(self) -> None:
        while True:
            await asyncio.sleep(self.SYNC_INTERVAL_SECONDS)
            try:
                await self._update_stats_message(validate_message=True)
            except Exception as exc:  # noqa: BLE001 - keep periodic loop alive
                logger.exception("Periodic stats sync failed: %s", exc)

    async def force_update_stats(self) -> bool:
        """Forces an immediate sync of the statistics message, but only applies changes when needed."""
        return await self._update_stats_message(validate_message=True)

    async def sync_stats_message(self) -> Dict[str, Any]:
        """RPC-friendly sync method for external callers (e.g. web_service)."""
        updated = await self._update_stats_message(validate_message=True)
        return {"success": True, "data": {"updated": updated}}

    async def recreate_stats_message(self) -> bool:
        """Deletes the current stats message and creates a fresh one with the current snapshot."""
        async with self._update_lock:
            admin_chat_id = self.bot.managers.headers.get("ADMIN_CHAT_ID")
            if not admin_chat_id:
                return False

            stats_obj = await self._get_stats()
            stats = self._normalize_stats_snapshot(stats_obj.model_dump())
            last_update_iso = self.update_detailed_stats(stats)
            message_text = self.format_stats_message(stats, last_update_iso=last_update_iso)

            if not await self._delete_old_message():
                return False

            return await self._create_new_stats_message(int(admin_chat_id), message_text)

    async def initialize_stats_message(self) -> None:
        """Initializes the stats message on bot startup."""
        await self._update_stats_message(validate_message=True)
        if self._periodic_task is None or self._periodic_task.done():
            self._periodic_task = asyncio.create_task(self._periodic_message_check())

    async def _on_ticket_created(self, ticket) -> None:
        self._schedule_update(delay_seconds=0.1)

    async def _on_ticket_updated(self, ticket) -> None:
        self._schedule_update(delay_seconds=0.1)

    async def _on_ticket_deleted(self, ticket) -> None:
        self._schedule_update(delay_seconds=0.1)
