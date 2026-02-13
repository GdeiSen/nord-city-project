# ./services/notification_service.py
from typing import TYPE_CHECKING, Optional, Dict, Any
import json
import re
from telegram.constants import ParseMode
from shared.constants import Dialogs, ServiceTicketStatus, Roles
from .base_service import BaseService
from utils.time_utils import now

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

    async def notify_new_ticket(self, ticket) -> Optional["Message"]:
        """
        Sends a notification to administrators about a new service ticket.

        Args:
            ticket: A dictionary representing the service ticket.

        Returns:
            The sent message object or None.
        """
        try:
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

            created_date = now().strftime("%d.%m.%Y %H:%M")

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

            # Link the message ID to the ticket status log (через сервис)
            if message and message.message_id:
                # Обновляем msid тикета на id сообщения в админ-чате
                await self.bot.services.service_ticket.update_service_ticket(ticket.id, {"msid": message.message_id})
                # Для новых тикетов user_id — это ticket.user_id (создатель)
                await self.bot.services.service_ticket.update_service_ticket_status(ticket.id, ServiceTicketStatus.NEW, message.message_id, ticket.user_id)
            return message
        except Exception as e:
            print(f"Error sending ticket notification to admin chat: {e}")
            return None

    async def handle_admin_reply(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> bool:
        try:
            print("[DEBUG] handle_admin_reply called")
            if not update.message or not update.message.reply_to_message:
                print("[DEBUG] No reply_to_message found")
                return False

            reply_to_message = update.message.reply_to_message
            user_id = update.message.from_user.id if update.message.from_user else None

            print(f"[DEBUG] Looking for ticket by msid={reply_to_message.message_id}")
            ticket = await self.bot.services.service_ticket.get_service_ticket_by_msid(
                reply_to_message.message_id
            )
            print(f"[DEBUG] Ticket found: {ticket}")
            if not ticket:
                print("[DEBUG] No ticket found for this message_id")
                return False

            message_text = update.message.text
            print(f"[DEBUG] Admin reply text: {message_text}")
            if not message_text:
                print("[DEBUG] No message text in admin reply")
                return False

            # Process different types of admin commands
            if re.search(r'принят[оа]', message_text.lower()):
                print("[DEBUG] Detected 'принято' command, processing acceptance...")
                await self._process_ticket_accepted(update, context, ticket, user_id)
                return True

            assigned_match = re.search(r'передан[оа]\s+["\']?([А-Яа-я\s]+)["\']?', message_text, re.IGNORECASE)
            if not assigned_match:
                 assigned_match = re.search(r'передал\s+["\']?([А-Яа-я\s]+)["\']?', message_text, re.IGNORECASE)
            if assigned_match:
                assignee = assigned_match.group(1).strip().title()
                print(f"[DEBUG] Detected 'передано' command, assignee: {assignee}")
                await self._process_ticket_assigned(update, context, ticket, user_id, assignee)
                return True

            if re.search(r'выполнен[оа]', message_text.lower()):
                print("[DEBUG] Detected 'выполнено' command, processing completion...")
                await self._process_ticket_completed(update, context, ticket, user_id)
                return True

            print("[DEBUG] No known admin command detected")
            return False
        except Exception as e:
            print(f"Error handling admin reply: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def ensure_user_exists(self, user_id: int):
        user = await self.bot.services.user.get_user_by_id(user_id)
        if not user:
            print(f"[DEBUG] User with id={user_id} not found, creating...")
            user = User(id=user_id, object_id=1, role=Roles.GUEST)
            await self.bot.services.user.create_user(user)

    async def _process_ticket_accepted(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE", ticket, user_id: int):
        print(f"[DEBUG] _process_ticket_accepted: ticket={ticket}, user_id={user_id}")
        await self.ensure_user_exists(user_id)
        log = await self.bot.services.service_ticket.update_service_ticket_status(ticket.id, ServiceTicketStatus.ACCEPTED, update.message.message_id, user_id)
        print(f"[DEBUG] update_service_ticket_status result: {log}")
        if log is not None:
            await self.bot.managers.message.reply_message(
                update, context, "ticket_accepted", payload=[str(ticket.id)]
            )
            await self.bot.services.stats.force_update_stats()

    async def _process_ticket_assigned(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE", ticket, user_id: int, assignee: str):
        print(f"[DEBUG] _process_ticket_assigned: ticket={ticket}, user_id={user_id}, assignee={assignee}")
        await self.ensure_user_exists(user_id)
        log = await self.bot.services.service_ticket.update_service_ticket_status(ticket.id, ServiceTicketStatus.ASSIGNED, update.message.message_id, user_id)
        print(f"[DEBUG] update_service_ticket_status result: {log}")
        if log is not None:
            await self.bot.managers.message.reply_message(
                update, context, "ticket_assigned", payload=[str(ticket.id), assignee]
            )
            await self.bot.services.stats.force_update_stats()

    async def _process_ticket_completed(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE", ticket, user_id: int):
        print(f"[DEBUG] _process_ticket_completed: ticket={ticket}, user_id={user_id}")
        await self.ensure_user_exists(user_id)
        log = await self.bot.services.service_ticket.update_service_ticket_status(ticket.id, ServiceTicketStatus.COMPLETED, update.message.message_id, user_id)
        print(f"[DEBUG] update_service_ticket_status result: {log}")
        if log is not None:
            await self.bot.managers.message.reply_message(
                update, context, "ticket_completed", payload=[str(ticket.id)]
            )
            await self.bot.services.stats.force_update_stats()
            await self.notify_ticket_completion(ticket.id, ticket.user_id)
            # Удаляем все reply-сообщения на исходное сообщение тикета
            await self._delete_all_ticket_replies(ticket)

    async def notify_ticket_completion(self, ticket_id: int, user_id: int):
        """Notifies a user about the completion of their ticket and prompts for feedback."""
        try:
            keyboard = self.bot.create_keyboard([
                [("rate_completion", f"{Dialogs.SERVICE_FEEDBACK}:{ticket_id}")]
            ])
            await self.bot.application.bot.send_message(
                chat_id=user_id,
                text=self.bot.get_text("ticket_completion_notification"),
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            print(f"Error notifying user about ticket completion: {e}")

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

            created_date = now().strftime("%d.%m.%Y %H:%M")

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
                print("[DEBUG] Admin chat ID not configured, skipping reply deletion")
                return

            # Получаем все логи тикета
            all_logs = await self.bot.services.service_ticket_log.get_all_service_ticket_logs()
            ticket_logs = [log for log in all_logs if getattr(log, 'ticket_id', None) == ticket.id]
            
            if not ticket_logs:
                print(f"[DEBUG] No logs found for ticket {ticket.id}, nothing to delete")
                return
            
            # Собираем все message_id из логов (кроме исходного сообщения тикета)
            original_msid = getattr(ticket, 'msid', None)
            message_ids_to_delete = set()  # Используем set для исключения дубликатов
            
            for log in ticket_logs:
                log_msid = getattr(log, 'msid', None)
                # Исключаем исходное сообщение тикета и None значения
                if log_msid and log_msid != original_msid:
                    message_ids_to_delete.add(log_msid)
            
            if not message_ids_to_delete:
                print(f"[DEBUG] No reply messages found to delete for ticket {ticket.id}")
                return
            
            print(f"[DEBUG] Found {len(message_ids_to_delete)} unique reply messages to delete for ticket {ticket.id}")
            
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
                        print(f"[DEBUG] Successfully deleted message {message_id}")
                    else:
                        failed_count += 1
                        print(f"[DEBUG] Failed to delete message {message_id}")
                except Exception as e:
                    failed_count += 1
                    print(f"[DEBUG] Error deleting message {message_id}: {e}")
            
            print(f"[DEBUG] Deletion summary: {deleted_count} deleted, {failed_count} failed out of {len(message_ids_to_delete)} total")
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