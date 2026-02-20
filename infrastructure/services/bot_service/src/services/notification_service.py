# ./services/notification_service.py
import asyncio
import json
from typing import TYPE_CHECKING, Optional, Dict, Any
import re
from telegram.constants import ParseMode
from shared.constants import Dialogs, ServiceTicketStatus, Roles
from .base_service import BaseService
from datetime import datetime
from utils.time_utils import now, TimeUtils

from telegram import Update, Message
from telegram.ext import ContextTypes
from shared.schemas import UserSchema, AuditLogSchema

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
        self._reminder_scheduler_task = None

    async def initialize(self) -> None:
        """Initializes the notification service by loading chat IDs from headers."""
        self._admin_chat_id = self.bot.managers.headers.get("ADMIN_CHAT_ID")
        self._chief_engineer_chat_id = self.bot.managers.headers.get("CHIEF_ENGINEER_CHAT_ID")
        self._reminder_scheduler_task = asyncio.create_task(self._run_reminder_scheduler())
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
            if ticket.meta:
                meta_dict = json.loads(ticket.meta)
                phone_number = meta_dict.get("phone_number", self.bot.get_text("phone_not_specified"))

            created_date = TimeUtils.format_time(ticket.created_at, "%d.%m.%Y %H:%M") if ticket.created_at else now().strftime("%d.%m.%Y %H:%M")

            # Format the notification text
            message_text = self.bot.get_text("ticket_to_admin_chat", [
                ticket.id,
                created_date,
                ticket.description or self.bot.get_text("description_not_specified"),
                ticket.location or self.bot.get_text("location_not_specified"),
                user_name,
                phone_number
            ])

            message = await self.bot.application.bot.send_message(
                chat_id=self._admin_chat_id,
                text=message_text,
                parse_mode=ParseMode.HTML
            )

            # Link the message ID to the ticket (для последующего edit/delete через сайт)
            if message and message.message_id:
                updated = await self.bot.services.service_ticket.update_service_ticket(
                    ticket.id,
                    {"msid": message.message_id},
                    _audit_context={
                        "source": "bot_service",
                        "assignee_id": 1,  # system
                        "meta": {"msid": message.message_id, "user_id": ticket.user_id},
                    },
                )
                if updated is None:
                    print(f"Failed to save msid for service_ticket {ticket.id}")
                    return {"success": False, "error": "msid_update_failed"}
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
            if not ticket.msid:
                return {"success": True, "error": None}

            user = await self.bot.services.user.get_user_by_id(ticket.user_id)
            user_name = self.bot.get_text("unknown_user")
            if user:
                user_name = f"{user.last_name or ''} {user.first_name or ''} {user.middle_name or ''}".strip()

            phone_number = self.bot.get_text("phone_not_specified")
            if ticket.meta:
                meta_dict = json.loads(ticket.meta) if isinstance(ticket.meta, str) else (ticket.meta or {})
                phone_number = meta_dict.get("phone_number", self.bot.get_text("phone_not_specified"))

            if not ticket.created_at:
                created_date = now().strftime("%d.%m.%Y %H:%M")
            elif isinstance(ticket.created_at, str):
                try:
                    from datetime import datetime as dt
                    parsed = dt.fromisoformat(ticket.created_at.replace("Z", "+00:00"))
                    created_date = TimeUtils.format_time(parsed, "%d.%m.%Y %H:%M")
                except (ValueError, TypeError):
                    created_date = now().strftime("%d.%m.%Y %H:%M")
            else:
                created_date = TimeUtils.format_time(ticket.created_at, "%d.%m.%Y %H:%M")

            payload = [
                ticket.id,
                created_date,
                ticket.description or self.bot.get_text("description_not_specified"),
                ticket.location or self.bot.get_text("location_not_specified"),
                user_name,
                phone_number,
            ]
            await self.bot.managers.message.edit_message(
                chat_id=self._admin_chat_id,
                message_id=ticket.msid,
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
            user = UserSchema(id=user_id, object_id=1, role=Roles.GUEST)
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
            if self._admin_chat_id and ticket.msid:
                try:
                    await self.bot.managers.message.delete_message(
                        chat_id=self._admin_chat_id,
                        message_id=ticket.msid,
                    )
                except Exception as e:
                    print(f"Error deleting ticket message (msid={ticket.msid}): {e}")
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
            if ticket.meta:
                meta_dict = json.loads(ticket.meta)
                phone_number = meta_dict.get("phone_number", self.bot.get_text('service_feedback_phone_not_specified'))

            created_date = TimeUtils.format_time(ticket.created_at, "%d.%m.%Y %H:%M") if ticket.created_at else now().strftime("%d.%m.%Y %H:%M")

            message_text = self.bot.get_text('service_feedback_to_chief_engineer', [
                created_date,
                ticket.description or self.bot.get_text("service_feedback_description_fallback"),
                ticket.location or self.bot.get_text("service_feedback_location_fallback"),
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
            if ticket.msid:
                message_ids_to_delete.add(ticket.msid)

            result = await self.bot.managers.database.audit_log.find_by_entity(
                entity_type="ServiceTicket",
                entity_id=ticket.id,
                model_class=AuditLogSchema,
            )
            ticket_logs = result.get("data", []) if result.get("success") else []
            for log in ticket_logs:
                meta = log.meta or {}
                log_msid = meta.get("msid")
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
                model_class=AuditLogSchema,
            )
            ticket_logs = result.get("data", []) if result.get("success") else []

            if not ticket_logs:
                return

            # Собираем все message_id из meta.msid (кроме исходного сообщения тикета)
            original_msid = ticket.msid
            message_ids_to_delete = set()

            for log in ticket_logs:
                meta = log.meta or {}
                log_msid = meta.get("msid")
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

    async def notify_guest_parking_request(
        self, req_id: int, data: dict, user_id: int
    ) -> None:
        """Отправляет заявку на гостевую парковку в канал администраторов."""
        try:
            if not self._admin_chat_id:
                return
            user = await self.bot.services.user.get_user_by_id(user_id)
            user_name = self.bot.get_text("unknown_user")
            legal_entity = ""
            if user:
                user_name = f"{user.last_name or ''} {user.first_name or ''} {user.middle_name or ''}".strip()
                legal_entity = user.legal_entity or ""

            arrival_date = data.get("arrival_date")
            date_str = (
                arrival_date.strftime("%d.%m.%Y")
                if isinstance(arrival_date, datetime)
                else str(arrival_date)[:10]
            )
            time_str = data.get("arrival_time", "")
            tenant_contact = data.get("tenant_phone", "")
            if user_name or legal_entity:
                tenant_contact = f"{tenant_contact} ({user_name}, {legal_entity})".strip()
            text = self.bot.get_text("guest_parking_to_admin", [
                date_str,
                time_str,
                data.get("license_plate", ""),
                data.get("car_make_color", ""),
                data.get("driver_phone", ""),
                tenant_contact,
            ])
            message = await self.bot.application.bot.send_message(
                chat_id=self._admin_chat_id,
                text=text,
                parse_mode=ParseMode.HTML,
            )
            if message and message.message_id:
                try:
                    await self.bot.managers.database.guest_parking.update(
                        entity_id=req_id,
                        update_data={"msid": message.message_id},
                        _audit_context={"source": "bot_service", "assignee_id": 1},
                    )
                except Exception as upd_e:
                    print(f"Error saving msid for guest parking {req_id}: {upd_e}")
        except Exception as e:
            print(f"Error notifying admin about guest parking request: {e}")

    async def schedule_guest_parking_reminder(
        self, req_id: int, data: dict
    ) -> None:
        """Заглушка: напоминания обрабатываются планировщиком check_guest_parking_reminders (каждую минуту)."""
        pass

    async def _run_reminder_scheduler(self) -> None:
        """Фоновый планировщик: каждую минуту проверяет заявки, по которым нужно отправить напоминание."""
        try:
            while True:
                try:
                    await self.check_guest_parking_reminders()
                except Exception as e:
                    print(f"Error in guest parking reminder scheduler: {e}")
                await asyncio.sleep(60)
        except asyncio.CancelledError:
            pass

    async def check_guest_parking_reminders(self) -> None:
        """
        Проверяет наличие заявок, по которым за 15 минут нужно отправить напоминание.
        Отправляет напоминания в канал администраторов.
        Использует TimeUtils.now() для согласованного часового пояса с сохранением заявок.
        """
        try:
            if not self._admin_chat_id:
                return
            reference_time = now()
            result = await self.bot.managers.database.guest_parking.find_due_for_reminder(
                reference_time_iso=reference_time.isoformat(),
            )
            if not result.get("success"):
                if result.get("error"):
                    print(f"Guest parking reminder check failed: {result['error']}")
                return
            items = result.get("data") or []
            if not items:
                return
            for item in items:
                req_id = item.get("id") if isinstance(item, dict) else getattr(item, "id", None)
                if req_id is None:
                    continue
                data = {
                    "license_plate": item.get("license_plate", "") if isinstance(item, dict) else (getattr(item, "license_plate", "") or ""),
                    "car_make_color": item.get("car_make_color", "") if isinstance(item, dict) else (getattr(item, "car_make_color", "") or ""),
                    "driver_phone": item.get("driver_phone", "") if isinstance(item, dict) else (getattr(item, "driver_phone", "") or ""),
                }
                try:
                    await self._send_guest_parking_reminder(req_id, data)
                    print(f"Guest parking reminder sent for request {req_id}")
                except Exception as e:
                    print(f"Error sending guest parking reminder for request {req_id}: {e}")
        except Exception as e:
            print(f"Error checking guest parking reminders: {e}")

    async def _send_guest_parking_reminder(self, req_id: int, data: dict) -> None:
        """Отправляет напоминание о гостевой парковке администраторам."""
        if not self._admin_chat_id:
            return
        text = self.bot.get_text("guest_parking_reminder", [
            data.get("license_plate", ""),
            data.get("car_make_color", ""),
            data.get("driver_phone", ""),
        ])
        await self.bot.application.bot.send_message(
            chat_id=self._admin_chat_id,
            text=text,
            parse_mode=ParseMode.HTML,
        )

    async def notify_new_guest_parking(self, req_id: int) -> Dict[str, Any]:
        """
        Отправляет заявку на гостевую парковку в чат администраторов (при создании с сайта).
        Сохраняет msid для последующего редактирования/удаления.
        """
        try:
            resp = await self.bot.managers.database.guest_parking.get_by_id(
                entity_id=req_id,
            )
            if not resp.get("success") or not resp.get("data"):
                return {"success": False, "error": "request_not_found"}
            req = resp["data"]
            if isinstance(req, dict):
                req_id_val = req.get("id")
                user_id = req.get("user_id")
                arrival_date = req.get("arrival_date")
                license_plate = req.get("license_plate", "")
                car_make_color = req.get("car_make_color", "")
                driver_phone = req.get("driver_phone", "")
                tenant_phone = req.get("tenant_phone", "")
            else:
                req_id_val = getattr(req, "id", None)
                user_id = getattr(req, "user_id", None)
                arrival_date = getattr(req, "arrival_date", None)
                license_plate = getattr(req, "license_plate", "") or ""
                car_make_color = getattr(req, "car_make_color", "") or ""
                driver_phone = getattr(req, "driver_phone", "") or ""
                tenant_phone = getattr(req, "tenant_phone", "") or ""

            user = await self.bot.services.user.get_user_by_id(user_id) if user_id else None
            user_name = self.bot.get_text("unknown_user")
            legal_entity = ""
            if user:
                user_name = f"{user.last_name or ''} {user.first_name or ''} {user.middle_name or ''}".strip()
                legal_entity = user.legal_entity or ""
            tenant_contact = tenant_phone or ""
            if user_name or legal_entity:
                tenant_contact = f"{tenant_contact} ({user_name}, {legal_entity})".strip()

            if arrival_date and hasattr(arrival_date, "strftime"):
                date_str = arrival_date.strftime("%d.%m.%Y")
                time_str = arrival_date.strftime("%H:%M")
            elif isinstance(arrival_date, str):
                parts = arrival_date.replace("Z", "").split("T")
                date_str = parts[0][:10] if parts else ""
                time_str = parts[1][:5] if len(parts) > 1 else ""
            else:
                date_str = str(arrival_date)[:10] if arrival_date else ""
                time_str = ""

            text = self.bot.get_text("guest_parking_to_admin", [
                date_str, time_str, license_plate, car_make_color, driver_phone, tenant_contact,
            ])
            message = await self.bot.application.bot.send_message(
                chat_id=self._admin_chat_id,
                text=text,
                parse_mode=ParseMode.HTML,
            )
            if message and message.message_id:
                upd = await self.bot.managers.database.guest_parking.update(
                    entity_id=req_id_val,
                    update_data={"msid": message.message_id},
                    _audit_context={"source": "bot_service", "assignee_id": 1},
                )
                if not upd.get("success"):
                    print(f"Failed to save msid for guest_parking {req_id_val}: {upd.get('error')}")
                    return {"success": False, "error": upd.get("error", "msid_update_failed")}
            return {"success": True, "error": None}
        except Exception as e:
            print(f"Error notifying new guest parking {req_id}: {e}")
            return {"success": False, "error": str(e)}

    async def edit_guest_parking_message(self, req_id: int) -> Dict[str, Any]:
        """Редактирует сообщение заявки в чате администраторов. Вызывать при изменении с сайта."""
        try:
            resp = await self.bot.managers.database.guest_parking.get_by_id(entity_id=req_id)
            if not resp.get("success") or not resp.get("data"):
                return {"success": False, "error": "request_not_found"}
            req = resp["data"]
            msid = req.get("msid") if isinstance(req, dict) else getattr(req, "msid", None)
            if not msid:
                return {"success": True, "error": None}
            if not self._admin_chat_id:
                return {"success": True, "error": None}

            if isinstance(req, dict):
                user_id = req.get("user_id")
                arrival_date = req.get("arrival_date")
                license_plate = req.get("license_plate", "")
                car_make_color = req.get("car_make_color", "")
                driver_phone = req.get("driver_phone", "")
                tenant_phone = req.get("tenant_phone", "")
            else:
                user_id = getattr(req, "user_id", None)
                arrival_date = getattr(req, "arrival_date", None)
                license_plate = getattr(req, "license_plate", "") or ""
                car_make_color = getattr(req, "car_make_color", "") or ""
                driver_phone = getattr(req, "driver_phone", "") or ""
                tenant_phone = getattr(req, "tenant_phone", "") or ""

            user = await self.bot.services.user.get_user_by_id(user_id) if user_id else None
            user_name = self.bot.get_text("unknown_user")
            legal_entity = ""
            if user:
                user_name = f"{user.last_name or ''} {user.first_name or ''} {user.middle_name or ''}".strip()
                legal_entity = user.legal_entity or ""
            tenant_contact = tenant_phone or ""
            if user_name or legal_entity:
                tenant_contact = f"{tenant_contact} ({user_name}, {legal_entity})".strip()

            if arrival_date and hasattr(arrival_date, "strftime"):
                date_str = arrival_date.strftime("%d.%m.%Y")
                time_str = arrival_date.strftime("%H:%M")
            elif isinstance(arrival_date, str):
                parts = arrival_date.replace("Z", "").split("T")
                date_str = parts[0][:10] if parts else ""
                time_str = parts[1][:5] if len(parts) > 1 else ""
            else:
                date_str = str(arrival_date)[:10] if arrival_date else ""
                time_str = ""

            payload = [date_str, time_str, license_plate, car_make_color, driver_phone, tenant_contact]
            await self.bot.managers.message.edit_message(
                chat_id=self._admin_chat_id,
                message_id=msid,
                text="guest_parking_to_admin",
                payload=payload,
            )
            admin_text = self.bot.get_text("guest_parking_updated_admin", [req_id])
            await self.bot.application.bot.send_message(
                chat_id=self._admin_chat_id,
                text=admin_text,
                parse_mode=ParseMode.HTML,
            )
            return {"success": True, "error": None}
        except Exception as e:
            print(f"Error editing guest parking message {req_id}: {e}")
            return {"success": False, "error": str(e)}

    async def delete_guest_parking_messages(self, req_id: int) -> Dict[str, Any]:
        """Удаляет сообщение заявки из чата администраторов. Вызывать перед удалением из БД."""
        try:
            resp = await self.bot.managers.database.guest_parking.get_by_id(entity_id=req_id)
            if not resp.get("success") or not resp.get("data"):
                return {"success": True, "error": None}
            req = resp["data"]
            msid = req.get("msid") if isinstance(req, dict) else getattr(req, "msid", None)
            if not msid or not self._admin_chat_id:
                return {"success": True, "error": None}
            await self.bot.managers.message.delete_message(
                chat_id=self._admin_chat_id,
                message_id=msid,
            )
            admin_text = self.bot.get_text("guest_parking_deleted_admin", [req_id])
            await self.bot.application.bot.send_message(
                chat_id=self._admin_chat_id,
                text=admin_text,
                parse_mode=ParseMode.HTML,
            )
            return {"success": True, "error": None}
        except Exception as e:
            print(f"Error deleting guest parking message {req_id}: {e}")
            return {"success": False, "error": str(e)}

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