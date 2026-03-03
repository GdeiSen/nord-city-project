# ./services/notification_service.py
import asyncio
import io
import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Dict, Any
import re
from urllib.parse import urlparse
import httpx
from telegram.constants import ParseMode
from telegram import InputFile
from shared.constants import Dialogs, ServiceTicketStatus, Roles
from shared.utils.storage_utils import extract_storage_path, to_public_storage_url
from .base_service import BaseService
from datetime import datetime
from utils.time_utils import now, TimeUtils

from telegram import Update, Message
from telegram.ext import ContextTypes
from shared.schemas import UserSchema, BotMessageRefSchema, StorageFileSchema

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

    async def _upsert_message_ref(
        self,
        *,
        entity_type: str,
        entity_id: int,
        chat_id: int,
        message_id: int,
        kind: str = "PRIMARY",
        meta: Optional[Dict[str, Any]] = None,
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

    async def _get_primary_message_ref(
        self,
        *,
        entity_type: str,
        entity_id: int,
    ) -> Any:
        result = await self.bot.managers.database.bot_message_ref.get_primary(
            entity_type=entity_type,
            entity_id=entity_id,
            model_class=BotMessageRefSchema,
        )
        return result.get("data") if result.get("success") else None

    async def _list_message_refs(
        self,
        *,
        entity_type: str,
        entity_id: int,
    ) -> list[Any]:
        result = await self.bot.managers.database.bot_message_ref.list_by_entity(
            entity_type=entity_type,
            entity_id=entity_id,
            model_class=BotMessageRefSchema,
        )
        return result.get("data", []) if result.get("success") else []

    async def _find_message_ref(
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

    async def _delete_message_refs(self, *, entity_type: str, entity_id: int) -> None:
        await self.bot.managers.database.bot_message_ref.delete_by_entity(
            entity_type=entity_type,
            entity_id=entity_id,
        )

    def _compose_broadcast_text(self, title: str, message: str) -> str:
        return self.bot.get_text(
            "bulk_notification_template",
            [
                str(title or "").strip(),
                str(message or "").strip(),
            ],
        ).strip()

    def _normalize_broadcast_attachments(self, attachment_urls: list[str] | None) -> list[str]:
        attachments: list[str] = []
        for raw_url in attachment_urls or []:
            normalized = to_public_storage_url(raw_url) or str(raw_url or "").strip()
            if normalized.startswith("http://") or normalized.startswith("https://"):
                attachments.append(normalized)
        seen: set[str] = set()
        unique_attachments: list[str] = []
        for attachment in attachments:
            if attachment in seen:
                continue
            seen.add(attachment)
            unique_attachments.append(attachment)
        return unique_attachments[:15]

    def _split_broadcast_attachments(self, attachment_urls: list[str]) -> tuple[list[str], list[str]]:
        image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"}
        images: list[str] = []
        documents: list[str] = []

        for attachment_url in attachment_urls:
            parsed = urlparse(attachment_url)
            extension = Path(parsed.path).suffix.lower()
            if extension in image_extensions:
                images.append(attachment_url)
            else:
                documents.append(attachment_url)

        return images[:10], documents[:10]

    def _get_broadcast_attachment_name(self, attachment_url: str) -> str:
        raw_name = Path(urlparse(attachment_url).path).name or "attachment"
        cleaned_name = re.sub(r"^(?:[a-f0-9]{32}_)+", "", raw_name, flags=re.IGNORECASE)
        return cleaned_name or raw_name

    def _get_internal_attachment_url(self, attachment_url: str) -> str | None:
        path = extract_storage_path(attachment_url)
        if not path:
            return None

        storage_base = os.getenv("STORAGE_SERVICE_HTTP_URL", "").strip().rstrip("/")
        if not storage_base:
            return None

        return f"{storage_base}/storage/{path}"

    async def _download_broadcast_document(self, attachment_url: str) -> tuple[str, bytes]:
        candidates: list[str] = []
        internal_url = self._get_internal_attachment_url(attachment_url)
        if internal_url:
            candidates.append(internal_url)
        if attachment_url not in candidates:
            candidates.append(attachment_url)

        last_error: Exception | None = None

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            for candidate_url in candidates:
                try:
                    response = await client.get(candidate_url)
                    response.raise_for_status()
                    return self._get_broadcast_attachment_name(attachment_url), response.content
                except Exception as exc:
                    last_error = exc

        raise RuntimeError(
            f"Failed to download broadcast attachment: {attachment_url}. "
            f"Last error: {last_error}"
        )

    @staticmethod
    def _extract_storage_file_meta(storage_file: Any) -> dict[str, Any]:
        if storage_file is None:
            return {}

        if isinstance(storage_file, dict):
            meta = storage_file.get("meta")
        else:
            meta = getattr(storage_file, "meta", None)

        if isinstance(meta, dict):
            return dict(meta)

        if isinstance(meta, str) and meta.strip():
            try:
                parsed = json.loads(meta)
                if isinstance(parsed, dict):
                    return parsed
            except (TypeError, ValueError):
                return {}

        return {}

    async def _get_storage_file_telegram_file_id(self, storage_path: str | None) -> str | None:
        if not storage_path:
            return None

        try:
            response = await self.bot.managers.database.storage_file.find_by_path(
                storage_path=storage_path,
                model_class=StorageFileSchema,
            )
        except Exception:
            return None

        if not response.get("success"):
            return None

        meta = self._extract_storage_file_meta(response.get("data"))
        telegram_file_id = str(meta.get("telegram_file_id") or "").strip()
        return telegram_file_id or None

    async def _persist_storage_file_telegram_file_id(
        self,
        *,
        storage_path: str | None,
        telegram_file_id: str | None,
    ) -> None:
        if not storage_path:
            return

        try:
            await self.bot.managers.database.storage_file.merge_meta_by_path(
                storage_path=storage_path,
                meta_updates={"telegram_file_id": telegram_file_id},
                model_class=StorageFileSchema,
            )
        except Exception:
            return

    async def _prepare_broadcast_document_refs(
        self,
        document_urls: list[str],
    ) -> list[dict[str, Any]]:
        document_refs: list[dict[str, Any]] = []

        for document_url in document_urls:
            storage_path = extract_storage_path(document_url)
            telegram_file_id = await self._get_storage_file_telegram_file_id(storage_path)
            document_refs.append(
                {
                    "url": document_url,
                    "storage_path": storage_path,
                    "telegram_file_id": telegram_file_id,
                }
            )

        return document_refs

    async def _send_broadcast_document(
        self,
        *,
        user_id: int,
        document_ref: dict[str, Any],
    ) -> None:
        telegram_file_id = str(document_ref.get("telegram_file_id") or "").strip()
        if telegram_file_id:
            try:
                await self.bot.application.bot.send_document(
                    chat_id=user_id,
                    document=telegram_file_id,
                )
                return
            except Exception:
                document_ref["telegram_file_id"] = None
                await self._persist_storage_file_telegram_file_id(
                    storage_path=document_ref.get("storage_path"),
                    telegram_file_id=None,
                )

        attachment_url = str(document_ref.get("url") or "").strip()
        filename, file_content = await self._download_broadcast_document(attachment_url)
        message = await self.bot.application.bot.send_document(
            chat_id=user_id,
            document=InputFile(io.BytesIO(file_content), filename=filename),
        )
        uploaded_file_id = getattr(getattr(message, "document", None), "file_id", None)
        if uploaded_file_id:
            document_ref["telegram_file_id"] = uploaded_file_id
            await self._persist_storage_file_telegram_file_id(
                storage_path=document_ref.get("storage_path"),
                telegram_file_id=str(uploaded_file_id),
            )

    async def _send_broadcast_to_user(
        self,
        *,
        user_id: int,
        text: str,
        image_urls: list[str],
        document_refs: list[dict[str, Any]],
    ) -> None:
        if not image_urls and not document_refs:
            await self.bot.application.bot.send_message(
                chat_id=user_id,
                text=text,
                parse_mode=ParseMode.HTML,
            )
            return

        if len(image_urls) == 1:
            await self.bot.application.bot.send_photo(
                chat_id=user_id,
                photo=image_urls[0],
            )
        elif len(image_urls) > 1:
            from telegram import InputMediaPhoto

            media = [InputMediaPhoto(media=image_url) for image_url in image_urls]
            await self.bot.application.bot.send_media_group(chat_id=user_id, media=media)

        await self.bot.application.bot.send_message(
            chat_id=user_id,
            text=text,
            parse_mode=ParseMode.HTML,
        )

        for document_ref in document_refs:
            await self._send_broadcast_document(
                user_id=user_id,
                document_ref=document_ref,
            )

    async def send_bulk_notification(
        self,
        *,
        user_ids: list[int],
        title: str,
        message: str,
        attachment_urls: list[str] | None = None,
    ) -> Dict[str, Any]:
        """Send a site-created announcement to multiple Telegram users."""
        normalized_user_ids = sorted({int(user_id) for user_id in (user_ids or [])})
        if not normalized_user_ids:
            return {"success": False, "error": "no_recipients"}

        text = self._compose_broadcast_text(title, message)
        if not text:
            return {"success": False, "error": "empty_message"}

        normalized_attachments = self._normalize_broadcast_attachments(attachment_urls)
        image_urls, document_urls = self._split_broadcast_attachments(normalized_attachments)
        document_refs = await self._prepare_broadcast_document_refs(document_urls)
        delivered_user_ids: list[int] = []
        failed_deliveries: list[dict[str, Any]] = []

        for user_id in normalized_user_ids:
            try:
                await self._send_broadcast_to_user(
                    user_id=user_id,
                    text=text,
                    image_urls=image_urls,
                    document_refs=document_refs,
                )
                delivered_user_ids.append(user_id)
            except Exception as exc:
                failed_deliveries.append(
                    {
                        "user_id": user_id,
                        "error": str(exc),
                    }
                )

        return {
            "success": True,
            "data": {
                "requested_count": len(normalized_user_ids),
                "sent_count": len(delivered_user_ids),
                "failed_count": len(failed_deliveries),
                "delivered_user_ids": delivered_user_ids,
                "failed_deliveries": failed_deliveries,
            },
            "error": None,
        }

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

            if message and message.message_id:
                await self._upsert_message_ref(
                    entity_type="ServiceTicket",
                    entity_id=ticket.id,
                    chat_id=int(self._admin_chat_id),
                    message_id=message.message_id,
                    kind="PRIMARY",
                    meta={"user_id": ticket.user_id},
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
            primary_ref = await self._get_primary_message_ref(
                entity_type="ServiceTicket",
                entity_id=ticket.id,
            )
            message_id = getattr(primary_ref, "message_id", None) or getattr(ticket, "msid", None)
            if not message_id:
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
                message_id=message_id,
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

            ticket = None
            message_ref = await self._find_message_ref(
                chat_id=update.effective_chat.id,
                message_id=reply_to_message.message_id,
                entity_type="ServiceTicket",
            )
            if message_ref is not None:
                ticket = await self.bot.services.service_ticket.get_service_ticket_by_id(message_ref.entity_id)
            if not ticket:
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
            await self._upsert_message_ref(
                entity_type="ServiceTicket",
                entity_id=ticket.id,
                chat_id=update.effective_chat.id,
                message_id=update.message.message_id,
                kind="REPLY",
                meta={"status": ServiceTicketStatus.IN_PROGRESS, "user_id": user_id},
            )
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
            await self._upsert_message_ref(
                entity_type="ServiceTicket",
                entity_id=ticket.id,
                chat_id=update.effective_chat.id,
                message_id=update.message.message_id,
                kind="REPLY",
                meta={"status": ServiceTicketStatus.ASSIGNED, "user_id": user_id, "assignee": assignee},
            )
            await self.bot.managers.message.reply_message(
                update, context, "ticket_assigned", payload=[str(ticket.id), assignee]
            )
            await self.bot.services.stats.force_update_stats()

    async def _process_ticket_completed(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE", ticket, user_id: int):
        await self.ensure_user_exists(user_id)
        log = await self.bot.services.service_ticket.update_service_ticket_status(ticket.id, ServiceTicketStatus.COMPLETED, update.message.message_id, user_id)
        if log is not None:
            await self._upsert_message_ref(
                entity_type="ServiceTicket",
                entity_id=ticket.id,
                chat_id=update.effective_chat.id,
                message_id=update.message.message_id,
                kind="REPLY",
                meta={"status": ServiceTicketStatus.COMPLETED, "user_id": user_id},
            )
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
            primary_ref = await self._get_primary_message_ref(
                entity_type="ServiceTicket",
                entity_id=ticket.id,
            )
            primary_message_id = getattr(primary_ref, "message_id", None) or getattr(ticket, "msid", None)
            if self._admin_chat_id and primary_message_id:
                try:
                    await self.bot.managers.message.delete_message(
                        chat_id=self._admin_chat_id,
                        message_id=primary_message_id,
                    )
                except Exception as e:
                    print(f"Error deleting ticket message (msid={primary_message_id}): {e}")
                await self._delete_message_refs(entity_type="ServiceTicket", entity_id=ticket.id)
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

            refs = await self._list_message_refs(entity_type="ServiceTicket", entity_id=ticket.id)
            message_ids_to_delete = {ref.message_id for ref in refs}
            if not message_ids_to_delete and ticket.msid:
                message_ids_to_delete.add(ticket.msid)

            for message_id in message_ids_to_delete:
                try:
                    await self.bot.managers.message.delete_message(
                        chat_id=self._admin_chat_id,
                        message_id=message_id,
                    )
                except Exception:
                    pass
            await self._delete_message_refs(entity_type="ServiceTicket", entity_id=ticket.id)
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

            refs = await self._list_message_refs(entity_type="ServiceTicket", entity_id=ticket.id)
            if not refs:
                return

            message_ids_to_delete = {ref.message_id for ref in refs if getattr(ref, "kind", "") != "PRIMARY"}
            
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
                tenant_contact,
            ])
            message = await self.bot.application.bot.send_message(
                chat_id=self._admin_chat_id,
                text=text,
                parse_mode=ParseMode.HTML,
            )
            if message and message.message_id:
                try:
                    await self._upsert_message_ref(
                        entity_type="GuestParkingRequest",
                        entity_id=req_id,
                        chat_id=int(self._admin_chat_id),
                        message_id=message.message_id,
                        kind="PRIMARY",
                    )
                except Exception as upd_e:
                    print(f"Error saving message ref for guest parking {req_id}: {upd_e}")
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
                }
                try:
                    await self._send_guest_parking_reminder(req_id, data)
                    print(f"Guest parking reminder sent for request {req_id}")
                except Exception as e:
                    print(f"Error sending guest parking reminder for request {req_id}: {e}")
        except Exception as e:
            print(f"Error checking guest parking reminders: {e}")

    async def _send_guest_parking_reminder(self, req_id: int, data: dict) -> None:
        """Отправляет напоминание о гостевой парковке администраторам. Учёт отправленных — в кэше database_service."""
        if not self._admin_chat_id:
            return
        text = self.bot.get_text("guest_parking_reminder", [
            data.get("license_plate", ""),
            data.get("car_make_color", ""),
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
                tenant_phone = req.get("tenant_phone", "")
            else:
                req_id_val = getattr(req, "id", None)
                user_id = getattr(req, "user_id", None)
                arrival_date = getattr(req, "arrival_date", None)
                license_plate = getattr(req, "license_plate", "") or ""
                car_make_color = getattr(req, "car_make_color", "") or ""
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
                date_str, time_str, license_plate, car_make_color, tenant_contact,
            ])
            message = await self.bot.application.bot.send_message(
                chat_id=self._admin_chat_id,
                text=text,
                parse_mode=ParseMode.HTML,
            )
            if message and message.message_id:
                upd = await self.bot.managers.database.bot_message_ref.upsert_message(
                    entity_type="GuestParkingRequest",
                    entity_id=req_id_val,
                    chat_id=int(self._admin_chat_id),
                    message_id=message.message_id,
                    kind="PRIMARY",
                )
                if not upd.get("success"):
                    print(f"Failed to save message ref for guest_parking {req_id_val}: {upd.get('error')}")
                    return {"success": False, "error": upd.get("error", "message_ref_update_failed")}
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
            primary_ref = await self._get_primary_message_ref(
                entity_type="GuestParkingRequest",
                entity_id=req_id,
            )
            msid = getattr(primary_ref, "message_id", None) or (req.get("msid") if isinstance(req, dict) else getattr(req, "msid", None))
            if not msid:
                return {"success": True, "error": None}
            if not self._admin_chat_id:
                return {"success": True, "error": None}

            if isinstance(req, dict):
                user_id = req.get("user_id")
                arrival_date = req.get("arrival_date")
                license_plate = req.get("license_plate", "")
                car_make_color = req.get("car_make_color", "")
                tenant_phone = req.get("tenant_phone", "")
            else:
                user_id = getattr(req, "user_id", None)
                arrival_date = getattr(req, "arrival_date", None)
                license_plate = getattr(req, "license_plate", "") or ""
                car_make_color = getattr(req, "car_make_color", "") or ""
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

            payload = [date_str, time_str, license_plate, car_make_color, tenant_contact]
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
            primary_ref = await self._get_primary_message_ref(
                entity_type="GuestParkingRequest",
                entity_id=req_id,
            )
            msid = getattr(primary_ref, "message_id", None) or (req.get("msid") if isinstance(req, dict) else getattr(req, "msid", None))
            if not msid or not self._admin_chat_id:
                return {"success": True, "error": None}
            await self.bot.managers.message.delete_message(
                chat_id=self._admin_chat_id,
                message_id=msid,
            )
            await self._delete_message_refs(entity_type="GuestParkingRequest", entity_id=req_id)
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
