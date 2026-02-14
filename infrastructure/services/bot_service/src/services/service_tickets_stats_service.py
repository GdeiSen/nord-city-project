# ./services/stats_service.py
import json
import os
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from zoneinfo import ZoneInfo
from services.base_service import BaseService
from typing import TYPE_CHECKING
from shared.entities.service_tickets_stats import ServiceTicketsStats
from telegram.error import BadRequest
if TYPE_CHECKING:
    from bot import Bot


class StatsService(BaseService):
    """Service for managing ticket statistics and auto-updating messages."""

    def __init__(self, bot: "Bot", json_file_path: str = "stats_data.json"):
        super().__init__(bot)
        self.json_file_path = json_file_path
        self.moscow_tz = ZoneInfo("Europe/Moscow")
        self._ensure_json_file()

    async def initialize(self) -> None:
        """Initializes the statistics service."""
        await self.initialize_stats_message()
        print("StatsService initialized")
        self.bot.managers.event.on('service_ticket_created', self._on_ticket_created)

    def _now(self):
        return datetime.now(self.moscow_tz)

    def _ensure_json_file(self):
        if not os.path.exists(self.json_file_path):
            self._save_data({
                "stats_message": {"chat_id": None, "message_id": None, "created_at": None},
                "detailed_stats": {"new_count": 0, "in_progress_count": 0, "new_tickets": [], "in_progress_tickets": [], "last_update": None}
            })

    def _load_data(self) -> Dict[str, Any]:
        try:
            with open(self.json_file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self._ensure_json_file()
            return self._load_data()

    def _save_data(self, data: Dict[str, Any]):
        with open(self.json_file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    def save_message_info(self, chat_id: Optional[int], message_id: Optional[int]):
        """Сохраняет информацию о сообщении со статистикой."""
        data = self._load_data()
        if chat_id is None or message_id is None:
            # Очищаем информацию о сообщении
            data["stats_message"] = {"chat_id": None, "message_id": None, "created_at": None}
        else:
            data["stats_message"] = {"chat_id": chat_id, "message_id": message_id, "created_at": self._now().isoformat()}
        self._save_data(data)

    def get_message_info(self) -> Optional[Dict[str, Any]]:
        data = self._load_data()
        msg_info = data.get("stats_message", {})
        return msg_info if msg_info.get("chat_id") and msg_info.get("message_id") else None

    def is_message_expired(self, hours_limit: int = 48) -> bool:
        message_info = self.get_message_info()
        if not message_info or not message_info.get("created_at"):
            return True
        created_at = datetime.fromisoformat(message_info["created_at"])
        return (self._now() - created_at) > timedelta(hours=hours_limit)

    def update_detailed_stats(self, stats: Dict[str, Any]):
        data = self._load_data()
        data["detailed_stats"] = {**stats, "last_update": self._now().isoformat()}
        self._save_data(data)

    def format_stats_message(self, stats: Dict[str, Any]) -> str:
        """Formats the statistics into a message string."""
        data = self._load_data()
        last_update_iso = data.get("detailed_stats", {}).get("last_update")
        time_str = datetime.fromisoformat(last_update_iso).strftime('%d.%m.%Y %H:%M') if last_update_iso else self._now().strftime('%d.%m.%Y %H:%M')
        
        new_tickets_str = ', '.join(map(str, stats.get('new_tickets', []))) or "нет"
        in_progress_tickets_str = ', '.join(map(str, stats.get('in_progress_tickets', []))) or "нет"

        return (
            f"<b>📊 Статистика заявок</b>\n\n"
            f"<b>Непринятых заявок:</b>\n{stats.get('new_count', 0)}\n"
            f"<b>Заявок в работе:</b>\n{stats.get('in_progress_count', 0)}\n"
            f"<b>Непринятые заявки:</b>\n{new_tickets_str}\n"
            f"<b>Заявки в работе:</b>\n{in_progress_tickets_str}"
            f"\n\n<b>Время обновления:</b> {time_str}"
        )

    async def _get_stats(self) -> ServiceTicketsStats:
        # Получаем агрегированную статистику через новый метод базы
        result = await self.bot.managers.database.service_ticket.get_stats(model_class=ServiceTicketsStats)
        if result["success"] and result["data"]:
            return result["data"]
        raise Exception(f"Failed to get stats: {result.get('error')}")
    
    async def _update_stats_message(self):
        """Updates the statistics message, creating a new one if necessary."""
        try:
            admin_chat_id = self.bot.managers.headers.get("ADMIN_CHAT_ID")
            if not admin_chat_id:
                return

            stats_obj = await self._get_stats()
            stats = stats_obj.to_dict() if hasattr(stats_obj, 'to_dict') else dict(stats_obj)
            self.update_detailed_stats(stats)
            message_text = self.format_stats_message(stats)
            message_info = self.get_message_info()

            if message_info and not self.is_message_expired():
                success = await self.bot.managers.message.edit_message(
                    chat_id=message_info["chat_id"], message_id=message_info["message_id"],
                    text=message_text, parse_mode='HTML'
                )
                if success:
                    return

            # Создаем новое сообщение, если редактирование не удалось или сообщение истекло
            await self._create_new_stats_message(admin_chat_id, message_text)
        except Exception as e:
            print(f"Error updating stats message: {e}")

    async def _create_new_stats_message(self, chat_id: str, message_text: str):
        """
        Создает новое сообщение со статистикой, предварительно удаляя старое.
        
        Args:
            chat_id: ID чата для отправки сообщения
            message_text: Текст сообщения со статистикой
        """
        await self._delete_old_message()

        try:
            await asyncio.sleep(0.5)

            message = await self.bot.application.bot.send_message(
                chat_id=int(chat_id), text=message_text, parse_mode='HTML'
            )

            try:
                await self.bot.application.bot.pin_chat_message(
                    chat_id=int(chat_id), message_id=message.message_id, disable_notification=True
                )
            except Exception:
                pass  # Pin may fail without admin permissions

            self.save_message_info(int(chat_id), message.message_id)
        except BadRequest as e:
            if "Chat not found" in str(e) or "chat not found" in str(e).lower():
                print(
                    f"[Stats] Admin chat not found (chat_id={chat_id}). "
                    "Ensure: 1) ADMIN_CHAT_ID in .env is correct, 2) the bot was added to that chat. "
                    "Stats message will not be sent until the chat is available."
                )
                self.save_message_info(None, None)
            else:
                print(f"Error creating new stats message: {e}")
                import traceback
                traceback.print_exc()
        except Exception as e:
            print(f"Error creating new stats message: {e}")
            import traceback
            traceback.print_exc()

    async def _delete_old_message(self) -> bool:
        """
        Удаляет старое сообщение со статистикой.
        
        Returns:
            True если сообщение было успешно удалено или не существовало,
            False если произошла ошибка при удалении.
        """
        message_info = self.get_message_info()
        if not message_info:
            return True

        chat_id = message_info.get("chat_id")
        message_id = message_info.get("message_id")

        if not chat_id or not message_id:
            self.save_message_info(None, None)
            return True
        
        try:
            deleted = await self.bot.managers.message.delete_message(
                chat_id=chat_id, message_id=message_id
            )

            if deleted:
                self.save_message_info(None, None)
                return True
            else:
                self.save_message_info(None, None)
                return False
        except Exception:
            self.save_message_info(None, None)
            return False

    async def _periodic_message_check(self):
        while True:
            await asyncio.sleep(3600)  # Check every hour
            if self.get_message_info() and self.is_message_expired():
                print("Stats message expired, recreating.")
                await self._update_stats_message()

    async def force_update_stats(self) -> bool:
        """Forces an immediate update of the statistics."""
        print("Force updating stats message...")
        await self._update_stats_message()
        return True
    
    async def recreate_stats_message(self) -> bool:
        """Deletes the old stats message and creates a new one."""
        print("Recreating stats message via command...")
        admin_chat_id = self.bot.managers.headers.get("ADMIN_CHAT_ID")
        if not admin_chat_id: return False
        stats_obj = await self._get_stats()
        stats = stats_obj.to_dict() if hasattr(stats_obj, 'to_dict') else dict(stats_obj)
        self.update_detailed_stats(stats)
        message_text = self.format_stats_message(stats)
        await self._create_new_stats_message(admin_chat_id, message_text)
        return True

    async def initialize_stats_message(self):
        """Initializes the stats message on bot startup."""
        await self._update_stats_message()
        asyncio.create_task(self._periodic_message_check())

    async def _on_ticket_created(self, ticket):
        await self._update_stats_message()