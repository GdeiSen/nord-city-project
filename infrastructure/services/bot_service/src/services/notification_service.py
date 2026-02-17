# ./services/notification_service.py
from typing import TYPE_CHECKING, Optional, Dict, Any
import json
import re
from telegram.constants import ParseMode
from shared.constants import Dialogs, ServiceTicketStatus, Roles
from .base_service import BaseService
from utils.time_utils import now, TimeUtils

from telegram import Update, Message
from telegram.ext import ContextTypes
from shared.models.user import User

if TYPE_CHECKING:
    from bot import Bot


class NotificationService(BaseService):
    """
    Service for centralized management of ticket notifications.

    Responsible for:
    - Notifying administrators about new tickets.
    - Processing administrator replies.
    - Notifying clients about ticket status changes.
    - Automatically sending quality surveys.
    """

    def __init__(self, bot: "Bot"):
        super().__init__(bot)
        self._admin_chat_id: Optional[str] = None
        self._chief_engineer_chat_id: Optional[str] = None

    async def initialize(self) -> None:
        """Initializes the notification service by loading chat IDs from headers."""
        self._admin_chat_id = self.bot.managers.headers.get("ADMIN_CHAT_ID")
        self._chief_engineer_chat_id = self.bot.managers.headers.get("CHIEF_ENGINEER_CHAT_ID")
        print("NotificationService initialized")

    async def notify_new_ticket(
        self, ticket=None, *, ticket_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Sends a notification to administrators about a new service ticket.

        Args:
            ticket: The service ticket object (when called from bot).
            ticket_id: Ticket ID to fetch (when called from web via RPC).

        Returns:
            Dict with success and error (JSON-serializable for RPC).
        """
        try:
            if ticket is None and ticket_id is not None:
                ticket = await self.bot.services.service_ticket.get_service_ticket_by_id(ticket_id)
            if ticket is None:
                return None
            if not self._admin_chat_id:
                print("Admin chat ID is not configured")
                return None

            # Get user info from the database (через сервис)
            user = await self.bot.services.user.get_user_by_id(ticket.user_id)
            user_name = self.bot.get_text("unknown_user")
            if user:
                user_name = f"{user.last_name or ''} {user.first_name or ''} {user.middle_name or ''}".strip()

            # Extract phone number from ticket meta
            phone_number = self.bot.get_text("phone_not_specified")
            meta = getattr(ticket, 'meta', None)
            if meta:
                meta_dict = json.loads(meta)
                phone_number = meta_dict.get("phone_number", self.bot.get_text("phone_not_specified"))

            created_at = getattr(ticket, "created_at", None)
            created_date = TimeUtils.format_time(created_at, "%d.%m.%Y %H:%M") if created_at else now().strftime("%d.%m.%Y %H:%M")

            # Format the notification text
            message_text = self.bot.get_text("ticket_to_admin_chat", [
                ticket.id,
                created_date,
                getattr(ticket, 'description', None) or self.bot.get_text("description_not_specified"),
                getattr(ticket, 'location', None) or self.bot.get_text("location_not_specified"),
                user_name,
                phone_number
            ])

            message = await self.bot.application.bot.send_message(
                chat_id=self._admin_chat_id,
                text=message_text,
                parse_mode=ParseMode.HTML
            )

            # Link the message ID to the ticket (одним update с meta для Telegram cleanup)
            if message and message.message_id:
                await self.bot.services.service_ticket.update_service_ticket(
                    ticket.id,
                    {"msid": message.message_id},
                    _audit_context={
                        "source": "bot_service",
                        "assignee_id": 1,  # system
                        "meta": {"msid": message.message_id, "user_id": ticket.user_id},
                    },
                )
            return {"success": True, "error": None}
        except Exception as e:
            print(f"Error sending ticket notification to admin chat: {e}")
            return {"success": False, "error": str(e)}

    async def edit_ticket_message(
        self, ticket=None, *, ticket_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Edits the ticket message in the admin chat with current data.
        Call when a ticket is edited via the website.

        Args:
            ticket: The ticket object (when called internally).
            ticket_id: Ticket ID to fetch (when called from web via RPC).
        """
        try:
            if ticket is None and ticket_id is not None:
                ticket = await self.bot.services.service_ticket.get_service_ticket_by_id(ticket_id)
            if ticket is None:
                return {"success": False, "error": "ticket_not_found"}
            if not self._admin_chat_id:
                return {"success": True, "error": None}
            msid = getattr(ticket, "msid", None)
            if not msid:
                return {"success": True, "error": None}

            user = await self.bot.services.user.get_user_by_id(ticket.user_id)
            user_name = self.bot.get_text("unknown_user")
            if user:
                user_name = f"{user.last_name or ''} {user.first_name or ''} {user.middle_name or ''}".strip()

            phone_number = self.bot.get_text("phone_not_specified")
            meta = getattr(ticket, "meta", None)
            if meta:
                meta_dict = json.loads(meta) if isinstance(meta, str) else (meta or {})
                phone_number = meta_dict.get("phone_number", self.bot.get_text("phone_not_specified"))

            created_at = getattr(ticket, "created_at", None) or (ticket.get("created_at") if hasattr(ticket, "get") else None)
            if not created_at:
                created_date = now().strftime("%d.%m.%Y %H:%M")
            elif isinstance(created_at, str):
                try:
                    from datetime import datetime as dt
                    parsed = dt.fromisoformat(created_at.replace("Z", "+00:00"))
                    created_date = TimeUtils.format_time(parsed, "%d.%m.%Y %H:%M")
                except (ValueError, TypeError):
                    created_date = now().strftime("%d.%m.%Y %H:%M")
            else:
                created_date = TimeUtils.format_time(created_at, "%d.%m.%Y %H:%M")

            payload = [
                ticket.id,
                created_date,
                getattr(ticket, "description", None) or self.bot.get_text("description_not_specified"),
                getattr(ticket, "location", None) or self.bot.get_text("location_not_specified"),
                user_name,
                phone_number,
            ]
            await self.bot.managers.message.edit_message(
                chat_id=self._admin_chat_id,
                message_id=msid,
                text="ticket_to_admin_chat",
                payload=payload,
            )
            admin_text = self.bot.get_text("ticket_updated_admin", [ticket.id])
            await self.bot.application.bot.send_message(
                chat_id=self._admin_chat_id,
                text=admin_text,
                parse_mode=ParseMode.HTML,
            )
            return {"success": True, "error": None}
        except Exception as e:
            print(f"Error editing ticket message: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}

    async def handle_admin_reply(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> bool:
        try:
            if not update.message or not update.message.reply_to_message:
                return False

            reply_to_message = update.message.reply_to_message
            user_id = update.message.from_user.id if update.message.from_user else None

            ticket = await self.bot.services.service_ticket.get_service_ticket_by_msid(
                reply_to_message.message_id
            )
            if not ticket:
                return False

            message_text = update.message.text
            if not message_text:
                return False

            if re.search(r'принят[оа]', message_text.lower()):
                await self._process_ticket_accepted(update, context, ticket, user_id)
                return True

            assigned_match = re.search(r'передан[оа]\s+["\']?([А-Яа-я\s]+)["\']?', message_text, re.IGNORECASE)
            if not assigned_match:
                 assigned_match = re.search(r'передал\s+["\']?([А-Яа-я\s]+)["\']?', message_text, re.IGNORECASE)
            if assigned_match:
                assignee = assigned_match.group(1).strip().title()
                await self._process_ticket_assigned(update, context, ticket, user_id, assignee)
                return True

            if re.search(r'выполнен[оа]', message_text.lower()):
                await self._process_ticket_completed(update, context, ticket, user_id)
                return True

            return False
        except Exception as e:
            print(f"Error handling admin reply: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def ensure_user_exists(self, user_id: int):
        user = await self.bot.services.user.get_user_by_id(user_id)
        if not user:
            user = User(id=user_id, object_id=1, role=Roles.GUEST)
            await self.bot.services.user.create_user(user)

    async def _process_ticket_accepted(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE", ticket, user_id: int):
        await self.ensure_user_exists(user_id)
        log = await self.bot.services.service_ticket.update_service_ticket_status(ticket.id, ServiceTicketStatus.IN_PROGRESS, update.message.message_id, user_id)
        if log is not None:
            await self.bot.managers.message.reply_message(
                update, context, "ticket_accepted", payload=[str(ticket.id)]
            )
            await self.bot.services.stats.force_update_stats()

    async def _process_ticket_assigned(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE", ticket, user_id: int, assignee: str):
        await self.ensure_user_exists(user_id)
        log = await self.bot.services.service_ticket.update_service_ticket_status(
            ticket.id, ServiceTicketStatus.ASSIGNED, update.message.message_id, user_id, assignee=assignee
        )
        if log is not None:
            await self.bot.managers.message.reply_message(
                update, context, "ticket_assigned", payload=[str(ticket.id), assignee]
            )
            await self.bot.services.stats.force_update_stats()

    async def _process_ticket_completed(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE", ticket, user_id: int):
        await self.ensure_user_exists(user_id)
        log = await self.bot.services.service_ticket.update_service_ticket_status(ticket.id, ServiceTicketStatus.COMPLETED, update.message.message_id, user_id)
        if log is not None:
            await self.bot.managers.message.reply_message(
                update, context, "ticket_completed", payload=[str(ticket.id)]
            )
            await self.notify_ticket_completion(ticket_id=ticket.id, user_id=ticket.user_id)

    async def notify_ticket_completion(
        self, ticket_id: int, user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Notifies a user about the completion of their ticket and prompts for feedback.
        Also deletes reply messages in the admin chat and updates stats.
        Can be called from bot (with user_id) or from web (ticket_id only).
        """
        try:
            ticket = await self.bot.services.service_ticket.get_service_ticket_by_id(ticket_id)
            if not ticket:
                return {"success": False, "error": "ticket_not_found"}
            uid = user_id if user_id is not None else ticket.user_id
            keyboard = self.bot.create_keyboard([
                [("rate_completion", f"{Dialogs.SERVICE_FEEDBACK}:{ticket_id}")]
            ])
            await self.bot.application.bot.send_message(
                chat_id=uid,
                text=self.bot.get_text("ticket_completion_notification"),
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
            await self.bot.services.stats.force_update_stats()
            await self._delete_all_ticket_replies(ticket)
            if self._admin_chat_id:
                msid = getattr(ticket, "msid", None)
                if msid:
                    try:
                        await self.bot.managers.message.delete_message(
                            chat_id=self._admin_chat_id,
                            message_id=msid,
                        )
                    except Exception as e:
                        print(f"Error deleting ticket message (msid={msid}): {e}")
                admin_text = self.bot.get_text("ticket_completed_admin", [ticket_id])
                await self.bot.application.bot.send_message(
                    chat_id=self._admin_chat_id,
                    text=admin_text,
                    parse_mode=ParseMode.HTML,
                )
            return {"success": True, "error": None}
        except Exception as e:
            print(f"Error notifying user about ticket completion: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}

    async def send_feedback_to_chief_engineer(self, ticket_id: int, feedback_message: str):
        """Sends feedback for a specific ticket to the chief engineer."""
        try:
            if not self._chief_engineer_chat_id:
                print("Chief engineer chat ID is not configured")
                return

            ticket = await self.bot.services.service_ticket.get_service_ticket_by_id(ticket_id)
            if not ticket:
                print(f"Ticket not found for feedback: {ticket_id}")
                return

            user = await self.bot.services.user.get_user_by_id(ticket.user_id)
            user_name = self.bot.get_text('service_feedback_unknown_user')
            if user:
                user_name = f"{user.last_name or ''} {user.first_name or ''} {user.middle_name or ''}".strip()

            phone_number = self.bot.get_text('service_feedback_phone_not_specified')
            meta = getattr(ticket, 'meta', None)
            if meta:
                meta_dict = json.loads(meta)
                phone_number = meta_dict.get("phone_number", self.bot.get_text('service_feedback_phone_not_specified'))

            created_at = getattr(ticket, "created_at", None)
            created_date = TimeUtils.format_time(created_at, "%d.%m.%Y %H:%M") if created_at else now().strftime("%d.%m.%Y %H:%M")

            message_text = self.bot.get_text('service_feedback_to_chief_engineer', [
                created_date,
                getattr(ticket, 'description', None) or 'Не указана',
                getattr(ticket, 'location', None) or 'Не указано',
                user_name,
                phone_number,
                feedback_message
            ])

            await self.bot.application.bot.send_message(
                chat_id=self._chief_engineer_chat_id,
                text=message_text,
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            print(f"Error sending feedback to chief engineer: {e}")

    async def delete_ticket_messages(
        self, ticket=None, *, ticket_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Deletes the ticket message and all reply messages from the admin chat.
        Call before deleting the ticket from DB.

        Args:
            ticket: The ticket object (when called internally).
            ticket_id: Ticket ID to fetch (when called from web via RPC).
        """
        try:
            if ticket is None and ticket_id is not None:
                ticket = await self.bot.services.service_ticket.get_service_ticket_by_id(ticket_id)
            if ticket is None:
                return {"success": False, "error": "ticket_not_found"}
            if not self._admin_chat_id:
                return {"success": True, "error": None}

            message_ids_to_delete = set()
            original_msid = getattr(ticket, "msid", None)
            if original_msid:
                message_ids_to_delete.add(original_msid)

            result = await self.bot.managers.database.audit_log.find_by_entity(
                entity_type="ServiceTicket",
                entity_id=ticket.id,
            )
            ticket_logs = result.get("data", []) if result.get("success") else []
            for log in ticket_logs:
                meta = log.get("meta", {}) if isinstance(log, dict) else getattr(log, "meta", None) or {}
                log_msid = meta.get("msid") if isinstance(meta, dict) else None
                if log_msid:
                    message_ids_to_delete.add(log_msid)

            for message_id in message_ids_to_delete:
                try:
                    await self.bot.managers.message.delete_message(
                        chat_id=self._admin_chat_id,
                        message_id=message_id,
                    )
                except Exception:
                    pass
            admin_text = self.bot.get_text("ticket_deleted_admin", [ticket.id])
            await self.bot.application.bot.send_message(
                chat_id=self._admin_chat_id,
                text=admin_text,
                parse_mode=ParseMode.HTML,
            )
            return {"success": True, "error": None}
        except Exception as e:
            print(f"Error deleting ticket messages: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}

    async def _delete_all_ticket_replies(self, ticket) -> None:
        """
        Удаляет все reply-сообщения на исходное сообщение тикета.
        
        Собирает все message_id из логов тикета и удаляет соответствующие сообщения
        из админ-чата, кроме исходного сообщения тикета.

        Args:
            ticket: Объект тикета с информацией о msid (исходное сообщение).
        """
        try:
            if not self._admin_chat_id:
                return

            # Получаем все audit entries для тикета
            result = await self.bot.managers.database.audit_log.find_by_entity(
                entity_type="ServiceTicket",
                entity_id=ticket.id,
            )
            ticket_logs = result.get("data", []) if result.get("success") else []

            if not ticket_logs:
                return

            # Собираем все message_id из meta.msid (кроме исходного сообщения тикета)
            original_msid = getattr(ticket, "msid", None)
            message_ids_to_delete = set()

            for log in ticket_logs:
                meta = log.get("meta", {}) if isinstance(log, dict) else getattr(log, "meta", None) or {}
                log_msid = meta.get("msid") if isinstance(meta, dict) else None
                # Исключаем исходное сообщение тикета и None значения
                if log_msid and log_msid != original_msid:
                    message_ids_to_delete.add(log_msid)
            
            if not message_ids_to_delete:
                return
            
            # Удаляем все собранные сообщения
            deleted_count = 0
            failed_count = 0
            for message_id in message_ids_to_delete:
                try:
                    success = await self.bot.managers.message.delete_message(
                        chat_id=self._admin_chat_id,
                        message_id=message_id
                    )
                    if success:
                        deleted_count += 1
                    else:
                        failed_count += 1
                except Exception:
                    failed_count += 1
        except Exception as e:
            print(f"Error deleting ticket reply messages: {e}")
            import traceback
            traceback.print_exc()

    def is_admin_chat(self, chat_id: int) -> bool:
        """
        Checks if a given chat ID is the configured administrative chat.

        Args:
            chat_id: The chat ID to check.

        Returns:
            True if it is the admin chat, False otherwise.
        """
        if not self._admin_chat_id:
            return False
        return str(chat_id) == str(self._admin_chat_id)