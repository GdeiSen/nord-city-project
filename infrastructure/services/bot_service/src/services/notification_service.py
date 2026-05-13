# ./services/notification_service.py
import asyncio
import io
import json
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Dict, Any
import re
from urllib.parse import urlparse
import httpx
from telegram.constants import ParseMode
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from shared.constants import Actions, Dialogs, ServiceTicketStatus, GuestParkingStatus
from shared.utils.storage_utils import extract_storage_path, to_public_storage_url
from .base_service import BaseService
from datetime import datetime
from utils.time_utils import now, TimeUtils

from telegram import Update, Message
from telegram.ext import ContextTypes
from shared.schemas import (
    UserSchema,
    BotMessageRefSchema,
    StorageFileSchema,
    ServiceTicketSchema,
    GuestParkingSchema,
)

if TYPE_CHECKING:
    from bot import Bot

logger = logging.getLogger(__name__)

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
        logger.info(
            "NotificationService initialized fallback_admin_chat=%s chief_engineer_chat=%s",
            bool(self._admin_chat_id),
            bool(self._chief_engineer_chat_id),
        )

    @staticmethod
    def _coerce_chat_id(value: Any) -> Optional[int]:
        try:
            if value is None:
                return None
            return int(str(value).strip())
        except (TypeError, ValueError):
            return None

    def _get_fallback_admin_chat_id(self) -> Optional[int]:
        return self._coerce_chat_id(self._admin_chat_id)

    async def _resolve_ticket_chat_id(self, ticket) -> Optional[int]:
        chat_id = await self.bot.services.chat_routing.resolve_chat_for_ticket(ticket=ticket)
        return chat_id if chat_id is not None else self._get_fallback_admin_chat_id()

    def _service_ticket_admin_keyboard(self, ticket) -> InlineKeyboardMarkup | None:
        status = str(self._get_entity_value(ticket, "status", ServiceTicketStatus.NEW)).upper()
        ticket_id = self._get_entity_value(ticket, "id")
        if not ticket_id or status in (ServiceTicketStatus.COMPLETED, ServiceTicketStatus.CANCELLED):
            return None

        buttons: list[InlineKeyboardButton] = []
        if status == ServiceTicketStatus.NEW:
            buttons.append(InlineKeyboardButton(
                self.bot.get_text("ticket_action_accept"),
                callback_data=f"service_ticket:accept:{ticket_id}",
            ))
            buttons.append(InlineKeyboardButton(
                self.bot.get_text("ticket_action_assign"),
                callback_data=f"service_ticket:assign:{ticket_id}",
            ))
        else:
            buttons.append(InlineKeyboardButton(
                self.bot.get_text("ticket_action_assign"),
                callback_data=f"service_ticket:assign:{ticket_id}",
            ))
            buttons.append(InlineKeyboardButton(
                self.bot.get_text("ticket_action_complete"),
                callback_data=f"service_ticket:complete:{ticket_id}",
            ))
        return InlineKeyboardMarkup([buttons])

    @staticmethod
    def _service_ticket_status_label(status: Any) -> str:
        value = str(status or ServiceTicketStatus.NEW).upper()
        return {
            ServiceTicketStatus.NEW: "Новая",
            ServiceTicketStatus.ACCEPTED: "Принята",
            ServiceTicketStatus.IN_PROGRESS: "В работе",
            ServiceTicketStatus.ASSIGNED: "Передана",
            ServiceTicketStatus.COMPLETED: "Выполнена",
            ServiceTicketStatus.CANCELLED: "Отменена",
        }.get(value, value)

    async def _resolve_guest_parking_chat_id(self, request=None, *, req_id: Optional[int] = None) -> Optional[int]:
        chat_id = await self.bot.services.chat_routing.resolve_chat_for_guest_parking(
            request=request,
            req_id=req_id,
        )
        return chat_id if chat_id is not None else self._get_fallback_admin_chat_id()

    @staticmethod
    def _parse_meta_dict(value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return dict(value)
        if isinstance(value, str) and value.strip():
            try:
                parsed = json.loads(value)
                if isinstance(parsed, dict):
                    return parsed
            except (TypeError, ValueError):
                return {}
        return {}

    @staticmethod
    def _build_delivery_meta(
        *,
        delivery_channel: str,
        target_chat_id: Optional[int] = None,
        fallback_used: Optional[bool] = None,
        status: Optional[str] = None,
        extra: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        meta = dict(extra or {})
        meta["delivery_channel"] = delivery_channel
        if target_chat_id is not None:
            meta["target_chat_id"] = int(target_chat_id)
        if fallback_used is not None:
            meta["fallback_used"] = bool(fallback_used)
        if status:
            meta["delivery_status"] = status
        return meta

    async def _append_delivery_audit_event(
        self,
        *,
        entity_type: str,
        entity_id: int,
        event_type: str,
        action: str,
        reason: str,
        audit_context: Optional[dict] = None,
        meta: Optional[dict[str, Any]] = None,
    ) -> None:
        await self.append_business_audit_event(
            entity_type=entity_type,
            entity_id=entity_id,
            event_type=event_type,
            action=action,
            audit_context=audit_context,
            reason=reason,
            meta=meta,
        )

    async def _delete_message_refs_with_messages(
        self,
        *,
        entity_type: str,
        entity_id: int,
    ) -> list[int]:
        refs = await self._list_message_refs(entity_type=entity_type, entity_id=entity_id)
        touched_chat_ids: set[int] = set()
        for ref in refs:
            chat_id = self._coerce_chat_id(getattr(ref, "chat_id", None))
            message_id = getattr(ref, "message_id", None)
            if chat_id is None or message_id is None:
                continue
            touched_chat_ids.add(chat_id)
            try:
                await self.bot.managers.message.delete_message(chat_id=chat_id, message_id=message_id)
            except Exception:
                pass
        await self._delete_message_refs(entity_type=entity_type, entity_id=entity_id)
        return sorted(touched_chat_ids)

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

    @staticmethod
    def _extract_ticket_id_from_message(message: Message | None) -> int | None:
        if message is None:
            return None

        raw_text = str(getattr(message, "text", None) or getattr(message, "caption", None) or "").strip()
        if not raw_text:
            return None

        match = re.search(r"#\s*(\d+)", raw_text)
        if not match:
            return None

        try:
            return int(match.group(1))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _get_entity_value(entity: Any, key: str, default: Any = None) -> Any:
        if isinstance(entity, dict):
            return entity.get(key, default)
        return getattr(entity, key, default)

    @staticmethod
    def _parse_datetime_value(value: Any) -> Optional[datetime]:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str) and value.strip():
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return None
        return None

    def _format_guest_parking_interval(self, request: Any, data: Optional[dict] = None) -> tuple[str, str]:
        data = data or {}
        start_raw = data.get("arrival_start_at") or self._get_entity_value(request, "arrival_start_at")
        end_raw = data.get("arrival_end_at") or self._get_entity_value(request, "arrival_end_at")
        fallback_raw = data.get("arrival_date") or self._get_entity_value(request, "arrival_date")
        start_at = self._parse_datetime_value(start_raw) or self._parse_datetime_value(fallback_raw)
        end_at = self._parse_datetime_value(end_raw)
        date_str = start_at.strftime("%d.%m.%Y") if start_at else (str(fallback_raw)[:10] if fallback_raw else "")
        if start_at and end_at:
            return date_str, f"{start_at.strftime('%H:%M')} - {end_at.strftime('%H:%M')}"
        if start_at:
            return date_str, start_at.strftime("%H:%M")
        return date_str, str(data.get("arrival_time") or "")

    @staticmethod
    def _guest_parking_status_label(status: Any) -> str:
        value = str(status or GuestParkingStatus.NEW).upper()
        return {
            GuestParkingStatus.NEW: "Ожидает подтверждения",
            GuestParkingStatus.APPROVED: "Подтверждена",
            GuestParkingStatus.REJECTED: "Отклонена",
            GuestParkingStatus.CANCELLED: "Отменена пользователем",
        }.get(value, value)

    def _guest_parking_admin_keyboard(self, req_id: int, status: Any = None) -> InlineKeyboardMarkup | None:
        if str(status or GuestParkingStatus.NEW).upper() != GuestParkingStatus.NEW:
            return None
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    self.bot.get_text("guest_parking_action_approve"),
                    callback_data=f"guest_parking:approve:{req_id}",
                ),
                InlineKeyboardButton(
                    self.bot.get_text("guest_parking_action_reject"),
                    callback_data=f"guest_parking:reject:{req_id}",
                ),
            ]
        ])

    def _guest_parking_cancel_keyboard(self, req_id: int) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    self.bot.get_text("guest_parking_action_cancel"),
                    callback_data=f"guest_parking:cancel:{req_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    self.bot.get_text("guest_parking_to_menu"),
                    callback_data=f"guest_parking:menu:{req_id}",
                )
            ],
        ])

    async def _resolve_ticket_from_admin_reply(
        self,
        *,
        chat_id: int,
        reply_to_message: Message,
    ):
        message_ref = await self._find_message_ref(
            chat_id=chat_id,
            message_id=reply_to_message.message_id,
            entity_type="ServiceTicket",
        )
        if message_ref is not None:
            ticket = await self.bot.services.service_ticket.get_service_ticket_by_id(message_ref.entity_id)
            if ticket is not None:
                return ticket

        ticket_id = self._extract_ticket_id_from_message(reply_to_message)
        if ticket_id is None:
            return None

        ticket = await self.bot.services.service_ticket.get_service_ticket_by_id(ticket_id)
        if ticket is None:
            return None

        try:
            await self._upsert_message_ref(
                entity_type="ServiceTicket",
                entity_id=ticket.id,
                chat_id=chat_id,
                message_id=reply_to_message.message_id,
                kind="PRIMARY",
                meta={"user_id": ticket.user_id, "restored_from_reply": True},
            )
        except Exception:
            pass

        return ticket

    async def _resolve_guest_parking_from_admin_reply(
        self,
        *,
        chat_id: int,
        reply_to_message: Message,
    ):
        message_ref = await self._find_message_ref(
            chat_id=chat_id,
            message_id=reply_to_message.message_id,
            entity_type="GuestParkingRequest",
        )
        if message_ref is not None:
            response = await self.bot.managers.database.guest_parking.get_by_id(
                entity_id=message_ref.entity_id,
                model_class=GuestParkingSchema,
            )
            if response.get("success") and response.get("data") is not None:
                return response["data"]

        request_id = self._extract_ticket_id_from_message(reply_to_message)
        if request_id is None:
            return None

        response = await self.bot.managers.database.guest_parking.get_by_id(
            entity_id=request_id,
            model_class=GuestParkingSchema,
        )
        if not response.get("success") or response.get("data") is None:
            return None
        request = response["data"]
        try:
            await self._upsert_message_ref(
                entity_type="GuestParkingRequest",
                entity_id=self._get_entity_value(request, "id"),
                chat_id=chat_id,
                message_id=reply_to_message.message_id,
                kind="PRIMARY",
                meta={"user_id": self._get_entity_value(request, "user_id"), "restored_from_reply": True},
            )
        except Exception:
            pass
        return request

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

    async def _download_broadcast_attachment(self, attachment_url: str) -> tuple[str, bytes]:
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
                _audit_context=self.derive_audit_context(
                    source_service="bot_service",
                    reason="storage_file_telegram_file_id_cached",
                    meta_updates={
                        "storage_meta_key": "telegram_file_id",
                        "storage_path": storage_path,
                    },
                ),
            )
        except Exception:
            return

    async def _prepare_broadcast_attachment_refs(
        self,
        attachment_urls: list[str],
    ) -> list[dict[str, Any]]:
        attachment_refs: list[dict[str, Any]] = []

        for attachment_url in attachment_urls:
            storage_path = extract_storage_path(attachment_url)
            telegram_file_id = await self._get_storage_file_telegram_file_id(storage_path)
            attachment_refs.append(
                {
                    "url": attachment_url,
                    "storage_path": storage_path,
                    "telegram_file_id": telegram_file_id,
                }
            )

        return attachment_refs

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
        filename, file_content = await self._download_broadcast_attachment(attachment_url)
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

    async def _send_broadcast_photo(
        self,
        *,
        user_id: int,
        image_ref: dict[str, Any],
    ) -> None:
        telegram_file_id = str(image_ref.get("telegram_file_id") or "").strip()
        if telegram_file_id:
            try:
                await self.bot.application.bot.send_photo(
                    chat_id=user_id,
                    photo=telegram_file_id,
                )
                return
            except Exception:
                image_ref["telegram_file_id"] = None
                await self._persist_storage_file_telegram_file_id(
                    storage_path=image_ref.get("storage_path"),
                    telegram_file_id=None,
                )

        attachment_url = str(image_ref.get("url") or "").strip()
        filename, file_content = await self._download_broadcast_attachment(attachment_url)
        message = await self.bot.application.bot.send_photo(
            chat_id=user_id,
            photo=InputFile(io.BytesIO(file_content), filename=filename),
        )
        photos = getattr(message, "photo", None) or []
        uploaded_file_id = getattr(photos[-1], "file_id", None) if photos else None
        if uploaded_file_id:
            image_ref["telegram_file_id"] = uploaded_file_id
            await self._persist_storage_file_telegram_file_id(
                storage_path=image_ref.get("storage_path"),
                telegram_file_id=str(uploaded_file_id),
            )

    async def _send_broadcast_photo_group(
        self,
        *,
        user_id: int,
        image_refs: list[dict[str, Any]],
    ) -> None:
        from telegram import InputMediaPhoto

        media: list[InputMediaPhoto] = []

        for image_ref in image_refs:
            telegram_file_id = str(image_ref.get("telegram_file_id") or "").strip()
            if telegram_file_id:
                media.append(InputMediaPhoto(media=telegram_file_id))
                continue

            attachment_url = str(image_ref.get("url") or "").strip()
            filename, file_content = await self._download_broadcast_attachment(attachment_url)
            input_file = InputFile(io.BytesIO(file_content), filename=filename)
            media.append(InputMediaPhoto(media=input_file))

        messages = await self.bot.application.bot.send_media_group(chat_id=user_id, media=media)
        for image_ref, message in zip(image_refs, messages or []):
            photos = getattr(message, "photo", None) or []
            uploaded_file_id = getattr(photos[-1], "file_id", None) if photos else None
            if uploaded_file_id:
                image_ref["telegram_file_id"] = uploaded_file_id
                await self._persist_storage_file_telegram_file_id(
                    storage_path=image_ref.get("storage_path"),
                    telegram_file_id=str(uploaded_file_id),
                )

    async def _send_broadcast_to_user(
        self,
        *,
        user_id: int,
        text: str,
        image_refs: list[dict[str, Any]],
        document_refs: list[dict[str, Any]],
    ) -> None:
        if not image_refs and not document_refs:
            await self.bot.application.bot.send_message(
                chat_id=user_id,
                text=text,
                parse_mode=ParseMode.HTML,
            )
            return

        if len(image_refs) == 1:
            await self._send_broadcast_photo(
                user_id=user_id,
                image_ref=image_refs[0],
            )
        elif len(image_refs) > 1:
            await self._send_broadcast_photo_group(
                user_id=user_id,
                image_refs=image_refs,
            )

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
        _audit_context: Optional[dict] = None,
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
        image_refs = await self._prepare_broadcast_attachment_refs(image_urls)
        document_refs = await self._prepare_broadcast_attachment_refs(document_urls)
        broadcast_id = int(now().timestamp() * 1000)

        await self.append_business_audit_event(
            entity_type="NotificationBroadcast",
            entity_id=broadcast_id,
            event_type="BROADCAST_STARTED",
            action="send",
            audit_context=self.derive_audit_context(
                _audit_context,
                source_service="bot_service",
                reason="notification_broadcast_started",
            ),
            reason="notification_broadcast_started",
            meta={
                "recipient_count": len(normalized_user_ids),
                "attachment_count": len(normalized_attachments),
                "image_count": len(image_refs),
                "document_count": len(document_refs),
            },
        )

        delivered_user_ids: list[int] = []
        failed_deliveries: list[dict[str, Any]] = []

        for user_id in normalized_user_ids:
            try:
                await self._send_broadcast_to_user(
                    user_id=user_id,
                    text=text,
                    image_refs=image_refs,
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

        await self.append_business_audit_event(
            entity_type="NotificationBroadcast",
            entity_id=broadcast_id,
            event_type="BROADCAST_COMPLETED",
            action="send",
            audit_context=self.derive_audit_context(
                _audit_context,
                source_service="bot_service",
                reason="notification_broadcast_completed",
            ),
            reason="notification_broadcast_completed",
            meta={
                "requested_count": len(normalized_user_ids),
                "sent_count": len(delivered_user_ids),
                "failed_count": len(failed_deliveries),
                "failed_user_ids": [
                    int(item["user_id"])
                    for item in failed_deliveries
                    if isinstance(item, dict) and item.get("user_id") is not None
                ],
            },
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
        self, ticket=None, *, ticket_id: Optional[int] = None, _audit_context: Optional[dict] = None
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
                return {"success": False, "error": "ticket_not_found"}

            object_id = getattr(ticket, "object_id", None)
            routed_chat_id = await self.bot.services.chat_routing.resolve_chat_for_ticket(ticket=ticket)
            target_chat_id = routed_chat_id if routed_chat_id is not None else self._get_fallback_admin_chat_id()
            fallback_used = routed_chat_id is None and target_chat_id is not None

            if target_chat_id is None:
                await self._append_delivery_audit_event(
                    entity_type="ServiceTicket",
                    entity_id=int(ticket.id),
                    event_type="DELIVERY_SKIPPED",
                    action="send",
                    reason="ticket_admin_chat_unresolved",
                    audit_context=self.derive_audit_context(
                        _audit_context,
                        source_service="bot_service",
                        reason="ticket_admin_chat_unresolved",
                    ),
                    meta=self._build_delivery_meta(
                        delivery_channel="telegram_admin_chat",
                        target_chat_id=None,
                        fallback_used=False,
                        status="skipped",
                        extra={"object_id": object_id},
                    ),
                )
                return {"success": True, "error": None}

            # Get user info from the database (через сервис)
            user = await self.bot.services.user.get_user_by_id(ticket.user_id)
            user_name = self.bot.get_text("unknown_user")
            if user:
                user_name = f"{user.last_name or ''} {user.first_name or ''} {user.middle_name or ''}".strip()

            object_name = self.bot.get_text("location_not_specified")
            object_id = getattr(ticket, "object_id", None) or (user.object_id if user else None)
            if object_id:
                obj = await self.bot.services.rental_object.get_object_by_id(object_id)
                if obj and obj.name:
                    object_name = obj.name

            # Extract phone number from ticket meta
            phone_number = self.bot.get_text("phone_not_specified")
            meta_dict = self._parse_meta_dict(ticket.meta)
            if meta_dict:
                phone_number = meta_dict.get("phone_number", self.bot.get_text("phone_not_specified"))

            created_date = TimeUtils.format_time(ticket.created_at, "%d.%m.%Y %H:%M") if ticket.created_at else now().strftime("%d.%m.%Y %H:%M")

            # Format the notification text
            message_text = self.bot.get_text("ticket_to_admin_chat", [
                ticket.id,
                created_date,
                self._service_ticket_status_label(ticket.status),
                object_name,
                ticket.category or self.bot.get_text("description_not_specified"),
                ticket.description or self.bot.get_text("description_not_specified"),
                ticket.location or self.bot.get_text("location_not_specified"),
                user_name,
                phone_number
            ])

            message = await self.bot.application.bot.send_message(
                chat_id=target_chat_id,
                text=message_text,
                reply_markup=self._service_ticket_admin_keyboard(ticket),
                parse_mode=ParseMode.HTML
            )

            if message and message.message_id:
                await self._upsert_message_ref(
                    entity_type="ServiceTicket",
                    entity_id=ticket.id,
                    chat_id=int(target_chat_id),
                    message_id=message.message_id,
                    kind="PRIMARY",
                    meta={"user_id": ticket.user_id},
                )
            await self._append_delivery_audit_event(
                entity_type="ServiceTicket",
                entity_id=int(ticket.id),
                event_type="DELIVERY_SUCCESS",
                action="send",
                reason="ticket_admin_chat_notified",
                audit_context=self.derive_audit_context(
                    _audit_context,
                    source_service="bot_service",
                    reason="ticket_admin_chat_notified",
                ),
                meta=self._build_delivery_meta(
                    delivery_channel="telegram_admin_chat",
                    target_chat_id=target_chat_id,
                    fallback_used=fallback_used,
                    status="success",
                    extra={
                        "object_id": object_id,
                        "telegram_message_id": getattr(message, "message_id", None),
                    },
                ),
            )
            logger.info(
                "Delivered service ticket to admin chat ticket_id=%s chat_id=%s fallback_used=%s object_id=%s message_id=%s",
                ticket.id,
                target_chat_id,
                fallback_used,
                object_id,
                getattr(message, "message_id", None),
            )
            return {"success": True, "error": None}
        except Exception as e:
            try:
                failed_entity_id = int(ticket.id) if ticket is not None and getattr(ticket, "id", None) is not None else int(ticket_id or 0)
            except (TypeError, ValueError):
                failed_entity_id = 0
            if failed_entity_id:
                await self._append_delivery_audit_event(
                    entity_type="ServiceTicket",
                    entity_id=failed_entity_id,
                    event_type="DELIVERY_FAILED",
                    action="send",
                    reason="ticket_admin_chat_notification_failed",
                    audit_context=self.derive_audit_context(
                        _audit_context,
                        source_service="bot_service",
                        reason="ticket_admin_chat_notification_failed",
                    ),
                    meta=self._build_delivery_meta(
                        delivery_channel="telegram_admin_chat",
                        status="failed",
                        extra={"error": str(e)},
                    ),
                )
            logger.exception(
                "Failed to deliver service ticket to admin chat ticket_id=%s: %s",
                getattr(ticket, "id", ticket_id),
                e,
            )
            return {"success": False, "error": str(e)}

    async def edit_ticket_message(
        self,
        ticket=None,
        *,
        ticket_id: Optional[int] = None,
        _audit_context: Optional[dict] = None,
        notify_admin_update: bool = True,
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
            target_chat_id = await self._resolve_ticket_chat_id(ticket)
            if target_chat_id is None:
                return {"success": True, "error": None}
            primary_ref = await self._get_primary_message_ref(
                entity_type="ServiceTicket",
                entity_id=ticket.id,
            )
            current_chat_id = self._coerce_chat_id(getattr(primary_ref, "chat_id", None))
            message_id = getattr(primary_ref, "message_id", None)
            if message_id and current_chat_id is not None and current_chat_id != target_chat_id:
                await self._delete_message_refs_with_messages(
                    entity_type="ServiceTicket",
                    entity_id=ticket.id,
                )
                return await self.notify_new_ticket(ticket=ticket, _audit_context=_audit_context)
            if not message_id:
                return await self.notify_new_ticket(ticket=ticket, _audit_context=_audit_context)
            current_chat_id = current_chat_id or target_chat_id

            user = await self.bot.services.user.get_user_by_id(ticket.user_id)
            user_name = self.bot.get_text("unknown_user")
            if user:
                user_name = f"{user.last_name or ''} {user.first_name or ''} {user.middle_name or ''}".strip()

            object_name = self.bot.get_text("location_not_specified")
            object_id = getattr(ticket, "object_id", None) or (user.object_id if user else None)
            if object_id:
                obj = await self.bot.services.rental_object.get_object_by_id(object_id)
                if obj and obj.name:
                    object_name = obj.name

            phone_number = self.bot.get_text("phone_not_specified")
            if ticket.meta:
                meta_dict = self._parse_meta_dict(ticket.meta)
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
                self._service_ticket_status_label(ticket.status),
                object_name,
                ticket.category or self.bot.get_text("description_not_specified"),
                ticket.description or self.bot.get_text("description_not_specified"),
                ticket.location or self.bot.get_text("location_not_specified"),
                user_name,
                phone_number,
            ]
            await self.bot.managers.message.edit_message(
                chat_id=current_chat_id,
                message_id=message_id,
                text="ticket_to_admin_chat",
                reply_markup=self._service_ticket_admin_keyboard(ticket),
                payload=payload,
            )
            if notify_admin_update:
                admin_text = self.bot.get_text("ticket_updated_admin", [ticket.id])
                await self.bot.application.bot.send_message(
                    chat_id=current_chat_id,
                    text=admin_text,
                    parse_mode=ParseMode.HTML,
                )
            await self._append_delivery_audit_event(
                entity_type="ServiceTicket",
                entity_id=int(ticket.id),
                event_type="DELIVERY_UPDATED",
                action="edit",
                reason="ticket_admin_chat_message_updated",
                audit_context=self.derive_audit_context(
                    _audit_context,
                    source_service="bot_service",
                    reason="ticket_admin_chat_message_updated",
                ),
                meta=self._build_delivery_meta(
                    delivery_channel="telegram_admin_chat",
                    target_chat_id=current_chat_id,
                    status="success",
                    extra={"telegram_message_id": message_id},
                ),
            )
            logger.info(
                "Updated service ticket admin message ticket_id=%s chat_id=%s message_id=%s",
                ticket.id,
                current_chat_id,
                message_id,
            )
            return {"success": True, "error": None}
        except Exception as e:
            try:
                failed_entity_id = int(ticket.id) if ticket is not None and getattr(ticket, "id", None) is not None else int(ticket_id or 0)
            except (TypeError, ValueError):
                failed_entity_id = 0
            if failed_entity_id:
                await self._append_delivery_audit_event(
                    entity_type="ServiceTicket",
                    entity_id=failed_entity_id,
                    event_type="DELIVERY_FAILED",
                    action="edit",
                    reason="ticket_admin_chat_message_update_failed",
                    audit_context=self.derive_audit_context(
                        _audit_context,
                        source_service="bot_service",
                        reason="ticket_admin_chat_message_update_failed",
                    ),
                    meta=self._build_delivery_meta(
                        delivery_channel="telegram_admin_chat",
                        status="failed",
                        extra={"error": str(e)},
                    ),
                )
            logger.exception(
                "Failed to update service ticket admin message ticket_id=%s: %s",
                getattr(ticket, "id", ticket_id),
                e,
            )
            return {"success": False, "error": str(e)}

    async def handle_admin_reply(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> bool:
        try:
            if not update.message or not update.message.reply_to_message:
                return False

            reply_to_message = update.message.reply_to_message
            user_id = update.message.from_user.id if update.message.from_user else None

            ticket = await self._resolve_ticket_from_admin_reply(
                chat_id=update.effective_chat.id,
                reply_to_message=reply_to_message,
            )
            if not ticket:
                parking_request = await self._resolve_guest_parking_from_admin_reply(
                    chat_id=update.effective_chat.id,
                    reply_to_message=reply_to_message,
                )
                if not parking_request:
                    return False

                message_text = (update.message.text or update.message.caption or "").strip()
                if not message_text:
                    return False
                lower_text = message_text.lower()
                if re.search(r'принят[оа]', lower_text):
                    await self._process_guest_parking_review(
                        update,
                        context,
                        parking_request,
                        GuestParkingStatus.APPROVED,
                        user_id,
                    )
                    return True
                if re.search(r'отклон[её]н[оа]|отклонить', lower_text):
                    reason = re.sub(r'^\s*(?:отклон[её]н[оа]|отклонить)\s*[:\-–—]?\s*', "", message_text, flags=re.IGNORECASE).strip()
                    await self._process_guest_parking_review(
                        update,
                        context,
                        parking_request,
                        GuestParkingStatus.REJECTED,
                        user_id,
                        reason=reason or None,
                    )
                    return True

                await self.bot.managers.message.reply_message(
                    update,
                    context,
                    "guest_parking_unknown_admin_command",
                )
                return True

            message_text = (update.message.text or update.message.caption or "").strip()
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

            await self.bot.managers.message.reply_message(
                update,
                context,
                "ticket_unknown_admin_command",
            )
            return True
        except Exception as e:
            logger.exception(
                "Failed to process admin reply chat_id=%s message_id=%s: %s",
                getattr(getattr(update, "effective_chat", None), "id", None),
                getattr(getattr(update, "message", None), "message_id", None),
                e,
            )
            return False

    async def _process_guest_parking_review(
        self,
        update: "Update",
        context: "ContextTypes.DEFAULT_TYPE",
        request,
        status_value: str,
        user_id: int,
        *,
        reason: Optional[str] = None,
    ):
        await self.ensure_user_exists(user_id)
        request_id = int(self._get_entity_value(request, "id"))
        rejection_reason = (reason or "").strip() or None
        if status_value == GuestParkingStatus.REJECTED and not rejection_reason:
            rejection_reason = "Заявка отклонена администратором."
        audit_context = self.build_telegram_actor_audit_context(
            telegram_user_id=user_id,
            reason="guest_parking_reviewed_from_admin_reply",
        )
        result = await self.bot.managers.database.guest_parking.update(
            entity_id=request_id,
            update_data={
                "status": status_value,
                "reviewed_by_user_id": user_id,
                "reviewed_at": now().isoformat(),
                "rejection_reason": rejection_reason,
            },
            model_class=GuestParkingSchema,
            _audit_context=audit_context,
        )
        if not result.get("success"):
            await self.bot.managers.message.reply_message(
                update,
                context,
                "error_processing_request",
            )
            return

        text_key = (
            "guest_parking_approved_admin"
            if status_value == GuestParkingStatus.APPROVED
            else "guest_parking_rejected_admin"
        )
        confirmation_message = await self.bot.managers.message.reply_message(
            update,
            context,
            text_key,
            payload=[str(request_id)],
        )
        if confirmation_message is not None:
            await self._upsert_message_ref(
                entity_type="GuestParkingRequest",
                entity_id=request_id,
                chat_id=confirmation_message.chat_id,
                message_id=confirmation_message.message_id,
                kind="REPLY",
                meta={"status": status_value, "user_id": user_id},
            )
        await self.notify_guest_parking_reviewed(
            req_id=request_id,
            _audit_context=audit_context,
            notify_admin=False,
        )

    async def handle_service_ticket_callback(
        self,
        update: "Update",
        context: "ContextTypes.DEFAULT_TYPE",
    ) -> bool:
        query = update.callback_query
        if query is None or not query.data:
            return False
        parts = query.data.split(":")
        if len(parts) != 3 or parts[0] != "service_ticket":
            return False

        action = parts[1]
        try:
            ticket_id = int(parts[2])
        except ValueError:
            return False

        ticket = await self.bot.services.service_ticket.get_service_ticket_by_id(ticket_id)
        if ticket is None:
            await query.message.reply_text(
                self.bot.get_text("ticket_not_found"),
                parse_mode=ParseMode.HTML,
            )
            return True

        if action == "user_cancel":
            actor_id = query.from_user.id if query.from_user else None
            ticket_user_id = getattr(ticket, "user_id", None)
            if actor_id != ticket_user_id:
                await query.message.reply_text(
                    self.bot.get_text("service_ticket_cancel_forbidden"),
                    parse_mode=ParseMode.HTML,
                )
                return True
            ticket_status = str(getattr(ticket, "status", "")).upper()
            if ticket_status not in (ServiceTicketStatus.NEW,):
                await query.message.reply_text(
                    self.bot.get_text("service_ticket_cancel_unavailable"),
                    parse_mode=ParseMode.HTML,
                )
                return True
            await self.bot.services.service_ticket.update_service_ticket_status(
                ticket.id,
                ServiceTicketStatus.CANCELLED,
                query.message.message_id if query.message else None,
                actor_id,
            )
            from telegram import InlineKeyboardMarkup, InlineKeyboardButton
            await query.edit_message_text(
                self.bot.get_text("service_ticket_cancelled_user", [str(ticket_id)]),
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        self.bot.get_text("service_feedback_to_main_menu"),
                        callback_data=f"service_ticket:to_menu:{ticket_id}",
                    )
                ]]),
            )
            admin_chat_id = await self._resolve_ticket_chat_id(ticket)
            if admin_chat_id:
                await self.bot.application.bot.send_message(
                    chat_id=admin_chat_id,
                    text=self.bot.get_text("service_ticket_cancelled_admin", [str(ticket_id)]),
                    parse_mode=ParseMode.HTML,
                )
            await self.edit_ticket_message(ticket_id=ticket_id, notify_admin_update=False)
            return True

        if action == "to_menu":
            await self.bot.managers.navigator.execute(Dialogs.MENU, update, context)
            return True

        chat_id = query.message.chat_id if query.message else None
        if not chat_id or not await self.is_admin_chat(chat_id):
            await query.message.reply_text(
                self.bot.get_text("ticket_admin_only_action"),
                parse_mode=ParseMode.HTML,
            )
            return True

        actor_id = query.from_user.id if query.from_user else None
        if actor_id is None:
            return True

        status = str(getattr(ticket, "status", ServiceTicketStatus.NEW)).upper()
        if status in (ServiceTicketStatus.COMPLETED, ServiceTicketStatus.CANCELLED):
            await query.message.reply_text(
                self.bot.get_text("ticket_already_completed", [str(ticket_id)]),
                parse_mode=ParseMode.HTML,
            )
            return True

        if action == "accept":
            updated = await self._apply_ticket_status_from_button(
                ticket,
                ServiceTicketStatus.IN_PROGRESS,
                actor_id,
                query.message.message_id,
                "ticket_accepted",
                [str(ticket_id)],
                "ticket_accepted_via_button",
            )
            if updated is None:
                await query.message.reply_text(
                    self.bot.get_text("error_processing_request"),
                    parse_mode=ParseMode.HTML,
                )
                return True
            await query.message.reply_text(
                self.bot.get_text("ticket_accepted", [str(ticket_id)]),
                parse_mode=ParseMode.HTML,
            )
            await self.edit_ticket_message(ticket_id=ticket_id, notify_admin_update=False)
            return True

        if action == "complete":
            updated = await self._apply_ticket_status_from_button(
                ticket,
                ServiceTicketStatus.COMPLETED,
                actor_id,
                query.message.message_id,
                "ticket_completed",
                [str(ticket_id)],
                "ticket_completed_via_button",
            )
            if updated is None:
                await query.message.reply_text(
                    self.bot.get_text("error_processing_request"),
                    parse_mode=ParseMode.HTML,
                )
                return True
            await query.message.reply_text(
                self.bot.get_text("ticket_completed", [str(ticket_id)]),
                parse_mode=ParseMode.HTML,
            )
            await self.notify_ticket_completion(ticket_id=ticket_id, user_id=ticket.user_id)
            return True

        if action == "assign":
            await query.message.reply_text(
                self.bot.get_text("ticket_assign_prompt", [str(ticket_id)]),
                parse_mode=ParseMode.HTML,
            )
            self._register_ticket_assign_input_handler(
                actor_id,
                ticket_id=ticket_id,
                admin_chat_id=int(chat_id),
                prompt_message_id=query.message.message_id,
            )
            return True

        return False

    def _build_ticket_assign_input_handler(
        self,
        *,
        ticket_id: int,
        admin_chat_id: int,
        prompt_message_id: int,
    ):
        async def handler(update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
            user_id = self.bot.get_user_id(update)
            chat_id = update.message.chat.id if update.message else None
            if chat_id != admin_chat_id:
                await self.bot.application.bot.send_message(
                    chat_id=admin_chat_id,
                    text=self.bot.get_text("ticket_assign_prompt_wrong_chat", [str(ticket_id)]),
                    parse_mode=ParseMode.HTML,
                )
                if user_id:
                    self._register_ticket_assign_input_handler(
                        user_id,
                        ticket_id=ticket_id,
                        admin_chat_id=admin_chat_id,
                        prompt_message_id=prompt_message_id,
                    )
                return

            assignee = (update.message.text or "").strip() if update.message else ""
            if not assignee:
                await self.bot.application.bot.send_message(
                    chat_id=admin_chat_id,
                    text=self.bot.get_text("ticket_assign_empty_assignee", [str(ticket_id)]),
                    parse_mode=ParseMode.HTML,
                )
                if user_id:
                    self._register_ticket_assign_input_handler(
                        user_id,
                        ticket_id=ticket_id,
                        admin_chat_id=admin_chat_id,
                        prompt_message_id=prompt_message_id,
                    )
                return

            ticket = await self.bot.services.service_ticket.get_service_ticket_by_id(ticket_id)
            if ticket is None:
                await self.bot.application.bot.send_message(
                    chat_id=admin_chat_id,
                    text=self.bot.get_text("ticket_not_found"),
                    parse_mode=ParseMode.HTML,
                )
                return

            updated = await self._apply_ticket_status_from_button(
                ticket,
                ServiceTicketStatus.ASSIGNED,
                user_id,
                getattr(update.message, "message_id", prompt_message_id),
                "ticket_assigned",
                [str(ticket_id), assignee],
                "ticket_assigned_via_button",
                assignee=assignee,
            )
            if updated is None:
                await self.bot.application.bot.send_message(
                    chat_id=admin_chat_id,
                    text=self.bot.get_text("error_processing_request"),
                    parse_mode=ParseMode.HTML,
                )
                return
            await self.bot.application.bot.send_message(
                chat_id=admin_chat_id,
                text=self.bot.get_text("ticket_assigned", [str(ticket_id), assignee]),
                parse_mode=ParseMode.HTML,
            )
            await self.edit_ticket_message(ticket_id=ticket_id, notify_admin_update=False)

        return handler

    def _register_ticket_assign_input_handler(
        self,
        user_id: int,
        *,
        ticket_id: int,
        admin_chat_id: int,
        prompt_message_id: int,
    ) -> None:
        self.bot.register_input_handler(
            user_id,
            Actions.TYPING,
            self._build_ticket_assign_input_handler(
                ticket_id=ticket_id,
                admin_chat_id=admin_chat_id,
                prompt_message_id=prompt_message_id,
            ),
            timeout_seconds=600,
            on_timeout=self._build_ticket_assign_timeout_handler(
                ticket_id=ticket_id,
                admin_chat_id=admin_chat_id,
            ),
        )

    def _build_ticket_assign_timeout_handler(self, *, ticket_id: int, admin_chat_id: int):
        async def on_timeout() -> None:
            await self.bot.application.bot.send_message(
                chat_id=admin_chat_id,
                text=self.bot.get_text("ticket_assign_timeout", [str(ticket_id)]),
                parse_mode=ParseMode.HTML,
            )

        return on_timeout

    async def _apply_ticket_status_from_button(
        self,
        ticket,
        status: str,
        user_id: int,
        message_id: int,
        text_key: str,
        payload: list[str],
        reason: str,
        *,
        assignee: Optional[str] = None,
    ):
        await self.ensure_user_exists(user_id)
        updated = await self.bot.services.service_ticket.update_service_ticket_status(
            ticket.id,
            status,
            message_id,
            user_id,
            assignee=assignee,
        )
        return updated

    async def handle_guest_parking_callback(
        self,
        update: "Update",
        context: "ContextTypes.DEFAULT_TYPE",
    ) -> bool:
        query = update.callback_query
        if query is None or not query.data:
            return False
        parts = query.data.split(":")
        if len(parts) != 3 or parts[0] != "guest_parking":
            return False

        action = parts[1]
        try:
            request_id = int(parts[2])
        except ValueError:
            return False

        if action == "menu":
            await query.answer()
            await self.bot.managers.navigator.execute(Dialogs.MENU, update, context)
            return True

        response = await self.bot.managers.database.guest_parking.get_by_id(
            entity_id=request_id,
            model_class=GuestParkingSchema,
        )
        if not response.get("success") or response.get("data") is None:
            await query.message.reply_text(
                self.bot.get_text("guest_parking_not_found"),
                parse_mode=ParseMode.HTML,
            )
            return True

        request = response["data"]
        current_status = str(self._get_entity_value(request, "status", GuestParkingStatus.NEW)).upper()
        actor_id = query.from_user.id if query.from_user else None

        if action == "user_cancel":
            request_user_id = self._get_entity_value(request, "user_id")
            if actor_id is None or int(request_user_id) != int(actor_id):
                await query.message.reply_text(
                    self.bot.get_text("guest_parking_cancel_forbidden"),
                    parse_mode=ParseMode.HTML,
                )
                return True
            if current_status != GuestParkingStatus.NEW:
                await query.message.reply_text(
                    self.bot.get_text("guest_parking_cancel_unavailable"),
                    parse_mode=ParseMode.HTML,
                )
                return True
            audit_context = self.build_telegram_actor_audit_context(
                telegram_user_id=actor_id,
                reason="guest_parking_cancelled_by_user_from_completion_message",
            )
            result = await self.bot.managers.database.guest_parking.update(
                entity_id=request_id,
                update_data={"status": GuestParkingStatus.CANCELLED},
                model_class=GuestParkingSchema,
                _audit_context=audit_context,
            )
            if not result.get("success"):
                await query.message.reply_text(
                    self.bot.get_text("error_processing_request"),
                    parse_mode=ParseMode.HTML,
                )
                return True
            date_str, time_str = self._format_guest_parking_interval(request)
            license_plate = self._get_entity_value(request, "license_plate", "") or ""
            await query.edit_message_text(
                self.bot.get_text("guest_parking_cancelled_user", [date_str, time_str, license_plate]),
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        self.bot.get_text("guest_parking_to_menu"),
                        callback_data=f"guest_parking:menu:{request_id}",
                    )
                ]]),
            )
            target_chat_id = await self._resolve_guest_parking_chat_id(request=request, req_id=request_id)
            if target_chat_id is not None:
                await self.bot.application.bot.send_message(
                    chat_id=target_chat_id,
                    text=self.bot.get_text("guest_parking_cancelled_admin", [str(request_id)]),
                    parse_mode=ParseMode.HTML,
                )
            await self.edit_guest_parking_message(
                req_id=request_id,
                _audit_context=audit_context,
                notify_admin_update=False,
            )
            return True

        if action in {"approve", "reject"}:
            chat_id = query.message.chat_id if query.message else None
            if not chat_id or not await self.is_admin_chat(chat_id):
                await query.message.reply_text(
                    self.bot.get_text("guest_parking_admin_only_action"),
                    parse_mode=ParseMode.HTML,
                )
                return True
            if current_status != GuestParkingStatus.NEW:
                await query.message.reply_text(
                    self.bot.get_text("guest_parking_already_reviewed", [
                        str(request_id),
                        self._guest_parking_status_label(current_status),
                    ]),
                    parse_mode=ParseMode.HTML,
                )
                return True

            status_value = GuestParkingStatus.APPROVED if action == "approve" else GuestParkingStatus.REJECTED
            rejection_reason = None
            if status_value == GuestParkingStatus.REJECTED:
                rejection_reason = "Заявка отклонена администратором."
            audit_context = self.build_telegram_actor_audit_context(
                telegram_user_id=actor_id,
                reason="guest_parking_reviewed_from_admin_button",
            )
            result = await self.bot.managers.database.guest_parking.update(
                entity_id=request_id,
                update_data={
                    "status": status_value,
                    "reviewed_by_user_id": actor_id,
                    "reviewed_at": now().isoformat(),
                    "rejection_reason": rejection_reason,
                },
                model_class=GuestParkingSchema,
                _audit_context=audit_context,
            )
            if not result.get("success"):
                await query.message.reply_text(
                    self.bot.get_text("error_processing_request"),
                    parse_mode=ParseMode.HTML,
                )
                return True

            await self.notify_guest_parking_reviewed(req_id=request_id, _audit_context=audit_context)
            return True

        if action == "cancel":
            request_user_id = self._get_entity_value(request, "user_id")
            if actor_id is None or int(request_user_id) != int(actor_id):
                await query.message.reply_text(
                    self.bot.get_text("guest_parking_cancel_forbidden"),
                    parse_mode=ParseMode.HTML,
                )
                return True
            if current_status != GuestParkingStatus.APPROVED:
                await query.message.reply_text(
                    self.bot.get_text("guest_parking_cancel_unavailable"),
                    parse_mode=ParseMode.HTML,
                )
                return True

            audit_context = self.build_telegram_actor_audit_context(
                telegram_user_id=actor_id,
                reason="guest_parking_cancelled_by_user",
            )
            result = await self.bot.managers.database.guest_parking.update(
                entity_id=request_id,
                update_data={"status": GuestParkingStatus.CANCELLED},
                model_class=GuestParkingSchema,
                _audit_context=audit_context,
            )
            if not result.get("success"):
                await query.message.reply_text(
                    self.bot.get_text("error_processing_request"),
                    parse_mode=ParseMode.HTML,
                )
                return True

            date_str, time_str = self._format_guest_parking_interval(request)
            license_plate = self._get_entity_value(request, "license_plate", "") or ""
            await query.edit_message_text(
                self.bot.get_text("guest_parking_cancelled_user", [date_str, time_str, license_plate]),
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(
                            self.bot.get_text("guest_parking_to_menu"),
                            callback_data=f"guest_parking:menu:{request_id}",
                        )
                    ]
                ]),
            )

            target_chat_id = await self._resolve_guest_parking_chat_id(request=request, req_id=request_id)
            if target_chat_id is not None:
                await self.bot.application.bot.send_message(
                    chat_id=target_chat_id,
                    text=self.bot.get_text("guest_parking_cancelled_admin", [str(request_id)]),
                    parse_mode=ParseMode.HTML,
                )
            await self.edit_guest_parking_message(
                req_id=request_id,
                _audit_context=audit_context,
                notify_admin_update=False,
            )
            return True

        return False

    async def ensure_user_exists(self, user_id: int):
        user = await self.bot.services.user.get_user_by_id(user_id)
        if not user:
            user = UserSchema(id=user_id, object_id=None)
            await self.bot.services.user.create_user(user)

    async def _process_ticket_accepted(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE", ticket, user_id: int):
        await self.ensure_user_exists(user_id)
        log = await self.bot.services.service_ticket.update_service_ticket_status(ticket.id, ServiceTicketStatus.IN_PROGRESS, update.message.message_id, user_id)
        if log is not None:
            confirmation_message = await self.bot.managers.message.reply_message(
                update, context, "ticket_accepted", payload=[str(ticket.id)]
            )
            if confirmation_message is not None:
                await self._upsert_message_ref(
                    entity_type="ServiceTicket",
                    entity_id=ticket.id,
                    chat_id=confirmation_message.chat_id,
                    message_id=confirmation_message.message_id,
                    kind="REPLY",
                    meta={"status": ServiceTicketStatus.IN_PROGRESS, "user_id": user_id},
                )
            await self.edit_ticket_message(ticket_id=ticket.id, notify_admin_update=False)

    async def _process_ticket_assigned(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE", ticket, user_id: int, assignee: str):
        await self.ensure_user_exists(user_id)
        log = await self.bot.services.service_ticket.update_service_ticket_status(
            ticket.id, ServiceTicketStatus.ASSIGNED, update.message.message_id, user_id, assignee=assignee
        )
        if log is not None:
            confirmation_message = await self.bot.managers.message.reply_message(
                update, context, "ticket_assigned", payload=[str(ticket.id), assignee]
            )
            if confirmation_message is not None:
                await self._upsert_message_ref(
                    entity_type="ServiceTicket",
                    entity_id=ticket.id,
                    chat_id=confirmation_message.chat_id,
                    message_id=confirmation_message.message_id,
                    kind="REPLY",
                    meta={"status": ServiceTicketStatus.ASSIGNED, "user_id": user_id, "assignee": assignee},
                )
            await self.edit_ticket_message(ticket_id=ticket.id, notify_admin_update=False)

    async def _process_ticket_completed(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE", ticket, user_id: int):
        await self.ensure_user_exists(user_id)
        log = await self.bot.services.service_ticket.update_service_ticket_status(ticket.id, ServiceTicketStatus.COMPLETED, update.message.message_id, user_id)
        if log is not None:
            telegram_audit_context = self.build_telegram_actor_audit_context(
                telegram_user_id=user_id,
                reason="ticket_completed_via_telegram_reply",
                meta_updates={
                    "reply_message_id": getattr(update.message, "message_id", None),
                    "reply_chat_id": getattr(getattr(update, "effective_chat", None), "id", None),
                },
            )
            confirmation_message = await self.bot.managers.message.reply_message(
                update, context, "ticket_completed", payload=[str(ticket.id)]
            )
            if confirmation_message is not None:
                await self._upsert_message_ref(
                    entity_type="ServiceTicket",
                    entity_id=ticket.id,
                    chat_id=confirmation_message.chat_id,
                    message_id=confirmation_message.message_id,
                    kind="REPLY",
                    meta={"status": ServiceTicketStatus.COMPLETED, "user_id": user_id},
                )
            await self.notify_ticket_completion(
                ticket_id=ticket.id,
                user_id=ticket.user_id,
                _audit_context=telegram_audit_context,
            )

    async def notify_ticket_completion(
        self, ticket_id: int, user_id: Optional[int] = None, _audit_context: Optional[dict] = None
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
            await self._append_delivery_audit_event(
                entity_type="ServiceTicket",
                entity_id=int(ticket_id),
                event_type="DELIVERY_SUCCESS",
                action="send",
                reason="ticket_completion_user_notified",
                audit_context=self.derive_audit_context(
                    _audit_context,
                    source_service="bot_service",
                    reason="ticket_completion_user_notified",
                ),
                meta={
                    "delivery_channel": "telegram_user_dm",
                    "target_user_id": int(uid),
                    "delivery_status": "success",
                },
            )
            logger.info(
                "Delivered ticket completion notification ticket_id=%s user_id=%s",
                ticket_id,
                uid,
            )
            await self._delete_all_ticket_replies(ticket)
            primary_ref = await self._get_primary_message_ref(
                entity_type="ServiceTicket",
                entity_id=ticket.id,
            )
            primary_message_id = getattr(primary_ref, "message_id", None)
            primary_chat_id = self._coerce_chat_id(getattr(primary_ref, "chat_id", None))
            if primary_chat_id is None:
                primary_chat_id = await self._resolve_ticket_chat_id(ticket)
            if primary_chat_id is not None and primary_message_id:
                try:
                    await self.bot.managers.message.delete_message(
                        chat_id=primary_chat_id,
                        message_id=primary_message_id,
                    )
                except Exception as e:
                    logger.warning(
                        "Failed to delete primary ticket message ticket_id=%s chat_id=%s message_id=%s: %s",
                        ticket.id,
                        primary_chat_id,
                        primary_message_id,
                        e,
                    )
                await self._delete_message_refs(entity_type="ServiceTicket", entity_id=ticket.id)
                admin_text = self.bot.get_text("ticket_completed_admin", [ticket_id])
                await self.bot.application.bot.send_message(
                    chat_id=primary_chat_id,
                    text=admin_text,
                    parse_mode=ParseMode.HTML,
                )
            return {"success": True, "error": None}
        except Exception as e:
            await self._append_delivery_audit_event(
                entity_type="ServiceTicket",
                entity_id=int(ticket_id),
                event_type="DELIVERY_FAILED",
                action="send",
                reason="ticket_completion_user_notification_failed",
                audit_context=self.derive_audit_context(
                    _audit_context,
                    source_service="bot_service",
                    reason="ticket_completion_user_notification_failed",
                ),
                meta={
                    "delivery_channel": "telegram_user_dm",
                    "delivery_status": "failed",
                    "target_user_id": int(user_id) if user_id is not None else None,
                    "error": str(e),
                },
            )
            logger.exception(
                "Failed to deliver ticket completion notification ticket_id=%s user_id=%s: %s",
                ticket_id,
                user_id,
                e,
            )
            return {"success": False, "error": str(e)}

    @staticmethod
    def _compose_service_feedback_body(answer: str, text: str | None = None) -> str:
        normalized_answer = str(answer or "").strip()
        normalized_text = str(text or "").strip()
        if normalized_answer and normalized_text:
            return f"{normalized_answer}: {normalized_text}"
        return normalized_answer or normalized_text

    async def send_service_ticket_feedback(
        self,
        *,
        ticket_id: int,
        feedback_answer: str,
        feedback_text: str | None = None,
        feedback_id: int | None = None,
        _audit_context: Optional[dict] = None,
    ) -> Dict[str, Any]:
        """Sends saved service completion feedback to the configured object recipient."""
        try:
            ticket = await self.bot.services.service_ticket.get_service_ticket_by_id(ticket_id)
            if not ticket:
                logger.warning("Ticket not found for manager feedback ticket_id=%s", ticket_id)
                return {"success": False, "error": "ticket_not_found"}

            user = await self.bot.services.user.get_user_by_id(ticket.user_id)
            user_name = self.bot.get_text('service_feedback_unknown_user')
            if user:
                user_name = f"{user.last_name or ''} {user.first_name or ''} {user.middle_name or ''}".strip()

            phone_number = self.bot.get_text('service_feedback_phone_not_specified')
            if ticket.meta:
                meta_dict = self._parse_meta_dict(ticket.meta)
                phone_number = meta_dict.get("phone_number", self.bot.get_text('service_feedback_phone_not_specified'))

            created_date = TimeUtils.format_time(ticket.created_at, "%d.%m.%Y %H:%M") if ticket.created_at else now().strftime("%d.%m.%Y %H:%M")
            feedback_message = self._compose_service_feedback_body(feedback_answer, feedback_text)

            message_text = self.bot.get_text('service_feedback_to_recipient', [
                created_date,
                ticket.description or self.bot.get_text("service_feedback_description_fallback"),
                ticket.location or self.bot.get_text("service_feedback_location_fallback"),
                user_name,
                phone_number,
                feedback_message
            ])

            recipient_user_id = await self.bot.services.chat_routing.resolve_feedback_recipient_user_id(ticket=ticket)
            if recipient_user_id is not None:
                await self.bot.application.bot.send_message(
                    chat_id=recipient_user_id,
                    text=message_text,
                    parse_mode=ParseMode.HTML,
                )
                await self._append_delivery_audit_event(
                    entity_type="ServiceTicket",
                    entity_id=int(ticket_id),
                    event_type="DELIVERY_SUCCESS",
                    action="send",
                    reason="service_ticket_feedback_delivered_to_recipient_user",
                    audit_context=self.derive_audit_context(
                        _audit_context,
                        source_service="bot_service",
                        reason="service_ticket_feedback_delivered_to_recipient_user",
                    ),
                    meta={
                        "delivery_channel": "telegram_user_dm",
                        "delivery_status": "success",
                        "target_user_id": int(recipient_user_id),
                        "feedback_id": int(feedback_id) if feedback_id is not None else None,
                    },
                )
                logger.info(
                    "Delivered service feedback ticket_id=%s recipient_user_id=%s feedback_id=%s",
                    ticket_id,
                    recipient_user_id,
                    feedback_id,
                )
                return {"success": True, "error": None}

            fallback_chat_id = self._coerce_chat_id(self._chief_engineer_chat_id)
            if fallback_chat_id is not None:
                await self.bot.application.bot.send_message(
                    chat_id=fallback_chat_id,
                    text=message_text,
                    parse_mode=ParseMode.HTML
                )
                await self._append_delivery_audit_event(
                    entity_type="ServiceTicket",
                    entity_id=int(ticket_id),
                    event_type="DELIVERY_SUCCESS",
                    action="send",
                    reason="service_ticket_feedback_delivered_to_fallback_chat",
                    audit_context=self.derive_audit_context(
                        _audit_context,
                        source_service="bot_service",
                        reason="service_ticket_feedback_delivered_to_fallback_chat",
                    ),
                    meta={
                        "delivery_channel": "telegram_chat",
                        "delivery_status": "success",
                        "target_chat_id": int(fallback_chat_id),
                        "feedback_id": int(feedback_id) if feedback_id is not None else None,
                        "fallback_used": True,
                    },
                )
                logger.info(
                    "Delivered service feedback ticket_id=%s fallback_chat_id=%s",
                    ticket_id,
                    fallback_chat_id,
                )
                return {"success": True, "error": None}
            await self._append_delivery_audit_event(
                entity_type="ServiceTicket",
                entity_id=int(ticket_id),
                event_type="DELIVERY_SKIPPED",
                action="send",
                reason="service_ticket_feedback_delivery_unresolved",
                audit_context=self.derive_audit_context(
                    _audit_context,
                    source_service="bot_service",
                    reason="service_ticket_feedback_delivery_unresolved",
                ),
                meta={
                    "delivery_channel": "telegram_user_dm",
                    "delivery_status": "skipped",
                    "feedback_id": int(feedback_id) if feedback_id is not None else None,
                },
            )
            return {"success": True, "error": None}
        except Exception as e:
            await self._append_delivery_audit_event(
                entity_type="ServiceTicket",
                entity_id=int(ticket_id),
                event_type="DELIVERY_FAILED",
                action="send",
                reason="service_ticket_feedback_delivery_failed",
                audit_context=self.derive_audit_context(
                    _audit_context,
                    source_service="bot_service",
                    reason="service_ticket_feedback_delivery_failed",
                ),
                meta={
                    "delivery_channel": "telegram_user_dm",
                    "delivery_status": "failed",
                    "feedback_id": int(feedback_id) if feedback_id is not None else None,
                    "error": str(e),
                },
            )
            logger.exception("Failed to deliver service feedback ticket_id=%s: %s", ticket_id, e)
            return {"success": False, "error": str(e)}

    async def send_feedback_to_managers(self, ticket_id: int, feedback_message: str):
        """Backward-compatible wrapper for legacy callers."""
        return await self.send_service_ticket_feedback(
            ticket_id=ticket_id,
            feedback_answer=feedback_message,
        )

    async def send_feedback_to_chief_engineer(self, ticket_id: int, feedback_message: str):
        """Backward-compatible alias for service feedback delivery."""
        return await self.send_feedback_to_managers(ticket_id, feedback_message)

    async def _find_tickets_for_object(self, object_id: int) -> list[Any]:
        response = await self.bot.managers.database.service_ticket.find(
            filters={"object_id": int(object_id)},
            model_class=ServiceTicketSchema,
        )
        if not response.get("success"):
            return []
        return response.get("data") or []

    async def _find_guest_parking_for_object(self, object_id: int) -> list[Any]:
        response = await self.bot.managers.database.guest_parking.find(
            filters={"object_id": int(object_id)},
            model_class=GuestParkingSchema,
        )
        if not response.get("success"):
            return []
        return response.get("data") or []

    async def resync_object_routes(self, object_id: int, _audit_context: Optional[dict] = None) -> Dict[str, Any]:
        """
        Re-sync active ticket and guest parking messages when an object's admin chat changes.
        """
        try:
            ticket_count = 0
            guest_parking_count = 0

            tickets = await self._find_tickets_for_object(object_id)
            active_statuses = {
                ServiceTicketStatus.NEW,
                ServiceTicketStatus.IN_PROGRESS,
                ServiceTicketStatus.ACCEPTED,
                ServiceTicketStatus.ASSIGNED,
            }
            for ticket in tickets:
                if getattr(ticket, "status", None) not in active_statuses:
                    continue
                await self.edit_ticket_message(ticket=ticket, _audit_context=_audit_context)
                ticket_count += 1

            guest_parking_requests = await self._find_guest_parking_for_object(object_id)
            for request in guest_parking_requests:
                request_id = getattr(request, "id", None)
                if request_id is None:
                    continue
                await self.edit_guest_parking_message(req_id=int(request_id), _audit_context=_audit_context)
                guest_parking_count += 1

            await self.append_business_audit_event(
                entity_type="Object",
                entity_id=int(object_id),
                event_type="ROUTE_RESYNC",
                action="sync",
                audit_context=self.derive_audit_context(
                    _audit_context,
                    source_service="bot_service",
                    reason="object_chat_routes_resynced",
                ),
                reason="object_chat_routes_resynced",
                meta={
                    "ticket_count": ticket_count,
                    "guest_parking_count": guest_parking_count,
                },
            )
            logger.info(
                "Resynced object chat routes object_id=%s ticket_count=%s guest_parking_count=%s",
                object_id,
                ticket_count,
                guest_parking_count,
            )

            return {
                "success": True,
                "data": {
                    "ticket_count": ticket_count,
                    "guest_parking_count": guest_parking_count,
                },
                "error": None,
            }
        except Exception as e:
            await self.append_business_audit_event(
                entity_type="Object",
                entity_id=int(object_id),
                event_type="ROUTE_RESYNC_FAILED",
                action="sync",
                audit_context=self.derive_audit_context(
                    _audit_context,
                    source_service="bot_service",
                    reason="object_chat_routes_resync_failed",
                ),
                reason="object_chat_routes_resync_failed",
                meta={"error": str(e)},
            )
            logger.exception("Failed to resync object chat routes object_id=%s: %s", object_id, e)
            return {"success": False, "error": str(e)}

    async def notify_user_deleted(
        self,
        *,
        user_id: int,
        username: Optional[str] = None,
        full_name: Optional[str] = None,
        cascade_counts: Optional[Dict[str, int]] = None,
        service_ticket_ids: Optional[list[int]] = None,
    ) -> Dict[str, Any]:
        """Notify admins that a user was removed and dependent entities were cascade-deleted."""
        try:
            if not self._admin_chat_id:
                return {"success": True, "error": None}

            counts = cascade_counts or {}
            ticket_ids = []
            for value in (service_ticket_ids or []):
                try:
                    ticket_ids.append(int(value))
                except (TypeError, ValueError):
                    continue

            username_text = str(username or "").strip()
            if username_text:
                if not username_text.startswith("@"):
                    username_text = f"@{username_text}"
            else:
                username_text = "не указан"

            full_name_text = str(full_name or "").strip() or "не указано"
            lines = [
                "Удален пользователь",
                f"ID: {int(user_id)}",
                f"Username: {username_text}",
                f"ФИО: {full_name_text}",
                "",
                "Каскадно удалено:",
                f"Заявки: {int(counts.get('service_tickets', 0))}",
                f"Обратная связь: {int(counts.get('feedbacks', 0))}",
                f"Опросы: {int(counts.get('poll_answers', 0))}",
                f"Гостевая парковка: {int(counts.get('guest_parking_requests', 0))}",
                f"Просмотры площадей: {int(counts.get('space_views', 0))}",
            ]

            if ticket_ids:
                ids_preview = ", ".join(str(item) for item in ticket_ids[:20])
                if len(ticket_ids) > 20:
                    ids_preview = f"{ids_preview}, ..."
                lines.append(f"ID удаленных заявок: {ids_preview}")

            await self.bot.application.bot.send_message(
                chat_id=self._admin_chat_id,
                text="\n".join(lines),
            )
            logger.info("Delivered user deletion notification user_id=%s", user_id)
            return {"success": True, "error": None}
        except Exception as e:
            logger.exception("Failed to notify admins about deleted user user_id=%s: %s", user_id, e)
            return {"success": False, "error": str(e)}

    async def delete_ticket_messages(
        self, ticket=None, *, ticket_id: Optional[int] = None, _audit_context: Optional[dict] = None
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
            touched_chat_ids = await self._delete_message_refs_with_messages(
                entity_type="ServiceTicket",
                entity_id=ticket.id,
            )
            if not touched_chat_ids:
                routed_chat_id = await self._resolve_ticket_chat_id(ticket)
                if routed_chat_id is not None:
                    touched_chat_ids = [routed_chat_id]
            admin_text = self.bot.get_text("ticket_deleted_admin", [ticket.id])
            for chat_id in touched_chat_ids:
                await self.bot.application.bot.send_message(
                    chat_id=chat_id,
                    text=admin_text,
                    parse_mode=ParseMode.HTML,
                )
            await self._append_delivery_audit_event(
                entity_type="ServiceTicket",
                entity_id=int(ticket.id),
                event_type="DELIVERY_DELETED",
                action="delete",
                reason="ticket_admin_chat_messages_deleted",
                audit_context=self.derive_audit_context(
                    _audit_context,
                    source_service="bot_service",
                    reason="ticket_admin_chat_messages_deleted",
                ),
                meta=self._build_delivery_meta(
                    delivery_channel="telegram_admin_chat",
                    status="success",
                    extra={"target_chat_ids": touched_chat_ids},
                ),
            )
            logger.info(
                "Deleted service ticket admin messages ticket_id=%s touched_chat_ids=%s",
                ticket.id,
                touched_chat_ids,
            )
            return {"success": True, "error": None}
        except Exception as e:
            try:
                failed_entity_id = int(ticket.id) if ticket is not None and getattr(ticket, "id", None) is not None else int(ticket_id or 0)
            except (TypeError, ValueError):
                failed_entity_id = 0
            if failed_entity_id:
                await self._append_delivery_audit_event(
                    entity_type="ServiceTicket",
                    entity_id=failed_entity_id,
                    event_type="DELIVERY_FAILED",
                    action="delete",
                    reason="ticket_admin_chat_message_delete_failed",
                    audit_context=self.derive_audit_context(
                        _audit_context,
                        source_service="bot_service",
                        reason="ticket_admin_chat_message_delete_failed",
                    ),
                    meta=self._build_delivery_meta(
                        delivery_channel="telegram_admin_chat",
                        status="failed",
                        extra={"error": str(e)},
                    ),
                )
            logger.exception(
                "Failed to delete service ticket admin messages ticket_id=%s: %s",
                getattr(ticket, "id", ticket_id),
                e,
            )
            return {"success": False, "error": str(e)}

    async def _delete_all_ticket_replies(self, ticket) -> None:
        """
        Удаляет все reply-сообщения на исходное сообщение тикета.
        
        Собирает все message_id из bot_message_refs и удаляет соответствующие сообщения
        из админ-чата, кроме исходного сообщения тикета.

        Args:
            ticket: Объект тикета, для которого уже существуют ссылки в bot_message_refs.
        """
        try:
            refs = await self._list_message_refs(entity_type="ServiceTicket", entity_id=ticket.id)
            if not refs:
                return

            reply_refs = [ref for ref in refs if getattr(ref, "kind", "") != "PRIMARY"]

            if not reply_refs:
                return

            for ref in reply_refs:
                chat_id = self._coerce_chat_id(getattr(ref, "chat_id", None))
                message_id = getattr(ref, "message_id", None)
                if chat_id is None or message_id is None:
                    continue
                try:
                    await self.bot.managers.message.delete_message(
                        chat_id=chat_id,
                        message_id=message_id,
                    )
                except Exception:
                    pass
        except Exception as e:
            logger.exception(
                "Failed to delete service ticket reply messages ticket_id=%s: %s",
                getattr(ticket, "id", None),
                e,
            )

    async def notify_guest_parking_request(
        self, req_id: int, data: dict, user_id: int
    ) -> None:
        """Отправляет заявку на гостевую парковку в канал администраторов."""
        try:
            target_chat_id = await self._resolve_guest_parking_chat_id(req_id=req_id)
            if target_chat_id is None:
                return
            user = await self.bot.services.user.get_user_by_id(user_id)
            user_name = self.bot.get_text("unknown_user")
            legal_entity = ""
            if user:
                user_name = f"{user.last_name or ''} {user.first_name or ''} {user.middle_name or ''}".strip()
                legal_entity = user.legal_entity or ""

            date_str, time_str = self._format_guest_parking_interval(None, data)
            tenant_contact = data.get("tenant_phone", "")
            if user_name or legal_entity:
                tenant_contact = f"{tenant_contact} ({user_name}, {legal_entity})".strip()
            text = self.bot.get_text("guest_parking_to_admin", [
                req_id,
                self._guest_parking_status_label(data.get("status")),
                date_str,
                time_str,
                data.get("license_plate", ""),
                tenant_contact,
            ])
            message = await self.bot.application.bot.send_message(
                chat_id=target_chat_id,
                text=text,
                reply_markup=self._guest_parking_admin_keyboard(req_id, data.get("status")),
                parse_mode=ParseMode.HTML,
            )
            if message and message.message_id:
                try:
                    await self._upsert_message_ref(
                        entity_type="GuestParkingRequest",
                        entity_id=req_id,
                        chat_id=int(target_chat_id),
                        message_id=message.message_id,
                        kind="PRIMARY",
                    )
                except Exception as upd_e:
                    logger.exception(
                        "Failed to save guest parking message ref request_id=%s chat_id=%s message_id=%s: %s",
                        req_id,
                        target_chat_id,
                        getattr(message, "message_id", None),
                        upd_e,
                    )
            logger.info(
                "Delivered guest parking request to admin chat request_id=%s chat_id=%s message_id=%s",
                req_id,
                target_chat_id,
                getattr(message, "message_id", None),
            )
        except Exception as e:
            logger.exception("Failed to deliver guest parking request request_id=%s: %s", req_id, e)

    async def schedule_guest_parking_reminder(
        self, req_id: int, data: dict
    ) -> None:
        """Заглушка: напоминания обрабатываются планировщиком check_guest_parking_reminders (каждую минуту)."""
        pass

    async def _run_reminder_scheduler(self) -> None:
        """Фоновый планировщик: каждую минуту проверяет заявки, по которым нужно отправить напоминание."""
        try:
            logger.info("Guest parking reminder scheduler started")
            while True:
                try:
                    await self.check_guest_parking_reminders()
                except Exception as e:
                    logger.exception("Guest parking reminder scheduler iteration failed: %s", e)
                await asyncio.sleep(60)
        except asyncio.CancelledError:
            logger.info("Guest parking reminder scheduler stopped")

    async def check_guest_parking_reminders(self) -> None:
        """
        Проверяет наличие заявок, по которым за 15 минут нужно отправить напоминание.
        Отправляет напоминания в канал администраторов.
        Использует TimeUtils.now() для согласованного часового пояса с сохранением заявок.
        """
        try:
            reference_time = now()
            result = await self.bot.managers.database.guest_parking.find_due_for_reminder(
                reference_time_iso=reference_time.isoformat(),
            )
            if not result.get("success"):
                if result.get("error"):
                    logger.warning(
                        "Guest parking reminder check failed: %s",
                        result["error"],
                    )
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
                }
                try:
                    await self._send_guest_parking_reminder(req_id, data)
                    logger.info("Delivered guest parking reminder request_id=%s", req_id)
                except Exception as e:
                    logger.exception(
                        "Failed to deliver guest parking reminder request_id=%s: %s",
                        req_id,
                        e,
                    )
        except Exception as e:
            logger.exception("Failed to check guest parking reminders: %s", e)

    async def _send_guest_parking_reminder(self, req_id: int, data: dict) -> None:
        """Отправляет напоминание о гостевой парковке администраторам. Учёт отправленных — в кэше database_service."""
        target_chat_id = await self._resolve_guest_parking_chat_id(req_id=req_id)
        if target_chat_id is None:
            return
        text = self.bot.get_text("guest_parking_reminder", [
            data.get("license_plate", ""),
        ])
        await self.bot.application.bot.send_message(
            chat_id=target_chat_id,
            text=text,
            parse_mode=ParseMode.HTML,
        )

    async def notify_new_guest_parking(self, req_id: int, _audit_context: Optional[dict] = None) -> Dict[str, Any]:
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
            object_id = req.get("object_id") if isinstance(req, dict) else getattr(req, "object_id", None)
            routed_chat_id = await self.bot.services.chat_routing.resolve_chat_for_guest_parking(
                request=req,
                req_id=req_id,
            )
            target_chat_id = routed_chat_id if routed_chat_id is not None else self._get_fallback_admin_chat_id()
            fallback_used = routed_chat_id is None and target_chat_id is not None
            if target_chat_id is None:
                await self._append_delivery_audit_event(
                    entity_type="GuestParkingRequest",
                    entity_id=int(req_id),
                    event_type="DELIVERY_SKIPPED",
                    action="send",
                    reason="guest_parking_admin_chat_unresolved",
                    audit_context=self.derive_audit_context(
                        _audit_context,
                        source_service="bot_service",
                        reason="guest_parking_admin_chat_unresolved",
                    ),
                    meta=self._build_delivery_meta(
                        delivery_channel="telegram_admin_chat",
                        status="skipped",
                        extra={"object_id": object_id},
                    ),
                )
                return {"success": True, "error": None}
            if isinstance(req, dict):
                req_id_val = req.get("id")
                user_id = req.get("user_id")
                arrival_date = req.get("arrival_date")
                arrival_start_at = req.get("arrival_start_at")
                arrival_end_at = req.get("arrival_end_at")
                license_plate = req.get("license_plate", "")
                tenant_phone = req.get("tenant_phone", "")
                status_value = req.get("status")
            else:
                req_id_val = getattr(req, "id", None)
                user_id = getattr(req, "user_id", None)
                arrival_date = getattr(req, "arrival_date", None)
                arrival_start_at = getattr(req, "arrival_start_at", None)
                arrival_end_at = getattr(req, "arrival_end_at", None)
                license_plate = getattr(req, "license_plate", "") or ""
                tenant_phone = getattr(req, "tenant_phone", "") or ""
                status_value = getattr(req, "status", None)

            user = await self.bot.services.user.get_user_by_id(user_id) if user_id else None
            user_name = self.bot.get_text("unknown_user")
            legal_entity = ""
            if user:
                user_name = f"{user.last_name or ''} {user.first_name or ''} {user.middle_name or ''}".strip()
                legal_entity = user.legal_entity or ""
            tenant_contact = tenant_phone or ""
            if user_name or legal_entity:
                tenant_contact = f"{tenant_contact} ({user_name}, {legal_entity})".strip()

            date_str, time_str = self._format_guest_parking_interval(
                {
                    "arrival_date": arrival_date,
                    "arrival_start_at": arrival_start_at,
                    "arrival_end_at": arrival_end_at,
                }
            )

            text = self.bot.get_text("guest_parking_to_admin", [
                req_id_val,
                self._guest_parking_status_label(status_value),
                date_str,
                time_str,
                license_plate,
                tenant_contact,
            ])
            message = await self.bot.application.bot.send_message(
                chat_id=target_chat_id,
                text=text,
                reply_markup=self._guest_parking_admin_keyboard(int(req_id_val or req_id), status_value),
                parse_mode=ParseMode.HTML,
            )
            if message and message.message_id:
                upd = await self.bot.managers.database.bot_message_ref.upsert_message(
                    entity_type="GuestParkingRequest",
                    entity_id=req_id_val,
                    chat_id=int(target_chat_id),
                    message_id=message.message_id,
                    kind="PRIMARY",
                )
                if not upd.get("success"):
                    logger.error(
                        "Failed to save guest parking message ref request_id=%s chat_id=%s: %s",
                        req_id_val,
                        target_chat_id,
                        upd.get("error"),
                    )
                    return {"success": False, "error": upd.get("error", "message_ref_update_failed")}
            await self._append_delivery_audit_event(
                entity_type="GuestParkingRequest",
                entity_id=int(req_id),
                event_type="DELIVERY_SUCCESS",
                action="send",
                reason="guest_parking_admin_chat_notified",
                audit_context=self.derive_audit_context(
                    _audit_context,
                    source_service="bot_service",
                    reason="guest_parking_admin_chat_notified",
                ),
                meta=self._build_delivery_meta(
                    delivery_channel="telegram_admin_chat",
                    target_chat_id=target_chat_id,
                    fallback_used=fallback_used,
                    status="success",
                    extra={
                        "object_id": object_id,
                        "telegram_message_id": getattr(message, "message_id", None),
                    },
                ),
            )
            logger.info(
                "Delivered new guest parking admin notification request_id=%s chat_id=%s fallback_used=%s message_id=%s",
                req_id,
                target_chat_id,
                fallback_used,
                getattr(message, "message_id", None),
            )
            return {"success": True, "error": None}
        except Exception as e:
            await self._append_delivery_audit_event(
                entity_type="GuestParkingRequest",
                entity_id=int(req_id),
                event_type="DELIVERY_FAILED",
                action="send",
                reason="guest_parking_admin_chat_notification_failed",
                audit_context=self.derive_audit_context(
                    _audit_context,
                    source_service="bot_service",
                    reason="guest_parking_admin_chat_notification_failed",
                ),
                meta=self._build_delivery_meta(
                    delivery_channel="telegram_admin_chat",
                    status="failed",
                    extra={"error": str(e)},
                ),
            )
            logger.exception("Failed to deliver new guest parking admin notification request_id=%s: %s", req_id, e)
            return {"success": False, "error": str(e)}

    async def edit_guest_parking_message(
        self,
        req_id: int,
        _audit_context: Optional[dict] = None,
        *,
        notify_admin_update: bool = True,
    ) -> Dict[str, Any]:
        """Редактирует сообщение заявки в чате администраторов. Вызывать при изменении с сайта."""
        try:
            resp = await self.bot.managers.database.guest_parking.get_by_id(entity_id=req_id)
            if not resp.get("success") or not resp.get("data"):
                return {"success": False, "error": "request_not_found"}
            req = resp["data"]
            target_chat_id = await self._resolve_guest_parking_chat_id(request=req, req_id=req_id)
            if target_chat_id is None:
                return {"success": True, "error": None}
            primary_ref = await self._get_primary_message_ref(
                entity_type="GuestParkingRequest",
                entity_id=req_id,
            )
            current_chat_id = self._coerce_chat_id(getattr(primary_ref, "chat_id", None))
            msid = getattr(primary_ref, "message_id", None) or (req.get("msid") if isinstance(req, dict) else getattr(req, "msid", None))
            if msid and current_chat_id is not None and current_chat_id != target_chat_id:
                await self._delete_message_refs_with_messages(
                    entity_type="GuestParkingRequest",
                    entity_id=req_id,
                )
                return await self.notify_new_guest_parking(req_id, _audit_context=_audit_context)
            if not msid:
                return await self.notify_new_guest_parking(req_id, _audit_context=_audit_context)
            current_chat_id = current_chat_id or target_chat_id

            if isinstance(req, dict):
                user_id = req.get("user_id")
                arrival_date = req.get("arrival_date")
                arrival_start_at = req.get("arrival_start_at")
                arrival_end_at = req.get("arrival_end_at")
                license_plate = req.get("license_plate", "")
                tenant_phone = req.get("tenant_phone", "")
                status_value = req.get("status")
            else:
                user_id = getattr(req, "user_id", None)
                arrival_date = getattr(req, "arrival_date", None)
                arrival_start_at = getattr(req, "arrival_start_at", None)
                arrival_end_at = getattr(req, "arrival_end_at", None)
                license_plate = getattr(req, "license_plate", "") or ""
                tenant_phone = getattr(req, "tenant_phone", "") or ""
                status_value = getattr(req, "status", None)

            user = await self.bot.services.user.get_user_by_id(user_id) if user_id else None
            user_name = self.bot.get_text("unknown_user")
            legal_entity = ""
            if user:
                user_name = f"{user.last_name or ''} {user.first_name or ''} {user.middle_name or ''}".strip()
                legal_entity = user.legal_entity or ""
            tenant_contact = tenant_phone or ""
            if user_name or legal_entity:
                tenant_contact = f"{tenant_contact} ({user_name}, {legal_entity})".strip()

            date_str, time_str = self._format_guest_parking_interval(
                {
                    "arrival_date": arrival_date,
                    "arrival_start_at": arrival_start_at,
                    "arrival_end_at": arrival_end_at,
                }
            )

            payload = [
                req_id,
                self._guest_parking_status_label(status_value),
                date_str,
                time_str,
                license_plate,
                tenant_contact,
            ]
            await self.bot.managers.message.edit_message(
                chat_id=current_chat_id,
                message_id=msid,
                text="guest_parking_to_admin",
                reply_markup=self._guest_parking_admin_keyboard(req_id, status_value),
                payload=payload,
            )
            if notify_admin_update:
                admin_text = self.bot.get_text("guest_parking_updated_admin", [req_id])
                await self.bot.application.bot.send_message(
                    chat_id=current_chat_id,
                    text=admin_text,
                    parse_mode=ParseMode.HTML,
                )
            await self._append_delivery_audit_event(
                entity_type="GuestParkingRequest",
                entity_id=int(req_id),
                event_type="DELIVERY_UPDATED",
                action="edit",
                reason="guest_parking_admin_chat_message_updated",
                audit_context=self.derive_audit_context(
                    _audit_context,
                    source_service="bot_service",
                    reason="guest_parking_admin_chat_message_updated",
                ),
                meta=self._build_delivery_meta(
                    delivery_channel="telegram_admin_chat",
                    target_chat_id=current_chat_id,
                    status="success",
                    extra={"telegram_message_id": msid},
                ),
            )
            logger.info(
                "Updated guest parking admin message request_id=%s chat_id=%s message_id=%s",
                req_id,
                current_chat_id,
                msid,
            )
            return {"success": True, "error": None}
        except Exception as e:
            await self._append_delivery_audit_event(
                entity_type="GuestParkingRequest",
                entity_id=int(req_id),
                event_type="DELIVERY_FAILED",
                action="edit",
                reason="guest_parking_admin_chat_message_update_failed",
                audit_context=self.derive_audit_context(
                    _audit_context,
                    source_service="bot_service",
                    reason="guest_parking_admin_chat_message_update_failed",
                ),
                meta=self._build_delivery_meta(
                    delivery_channel="telegram_admin_chat",
                    status="failed",
                    extra={"error": str(e)},
                ),
            )
            logger.exception("Failed to update guest parking admin message request_id=%s: %s", req_id, e)
            return {"success": False, "error": str(e)}

    async def notify_guest_parking_reviewed(
        self,
        req_id: int,
        _audit_context: Optional[dict] = None,
        *,
        notify_admin: bool = True,
    ) -> Dict[str, Any]:
        """Уведомляет арендатора и обновляет админское сообщение после подтверждения/отклонения парковки."""
        try:
            resp = await self.bot.managers.database.guest_parking.get_by_id(
                entity_id=req_id,
                model_class=GuestParkingSchema,
            )
            if not resp.get("success") or not resp.get("data"):
                return {"success": False, "error": "request_not_found"}
            req = resp["data"]
            user_id = self._get_entity_value(req, "user_id")
            status_value = str(self._get_entity_value(req, "status", GuestParkingStatus.NEW)).upper()
            license_plate = self._get_entity_value(req, "license_plate", "") or ""
            rejection_reason = self._get_entity_value(req, "rejection_reason", "") or "Заявка отклонена администратором."
            date_str, time_str = self._format_guest_parking_interval(req)

            if status_value in {GuestParkingStatus.APPROVED, GuestParkingStatus.REJECTED} and user_id:
                target_chat_id = await self._resolve_guest_parking_chat_id(req_id=req_id)
                user_chat_id = await self._resolve_guest_parking_chat_id(request=req, req_id=req_id)
                user_chat_id = int(user_id) if user_id else user_chat_id
                text_key = (
                    "guest_parking_approved_user"
                    if status_value == GuestParkingStatus.APPROVED
                    else "guest_parking_rejected_user"
                )
                payload = [date_str, time_str, license_plate]
                if status_value == GuestParkingStatus.REJECTED:
                    payload.append(rejection_reason)
                try:
                    reply_markup = (
                        self._guest_parking_cancel_keyboard(req_id)
                        if status_value == GuestParkingStatus.APPROVED
                        else None
                    )
                    await self.bot.application.bot.send_message(
                        chat_id=user_chat_id,
                        text=self.bot.get_text(text_key, payload),
                        reply_markup=reply_markup,
                        parse_mode=ParseMode.HTML,
                    )
                    await self._append_delivery_audit_event(
                        entity_type="GuestParkingRequest",
                        entity_id=int(req_id),
                        event_type="DELIVERY_SUCCESS",
                        action="send",
                        reason="guest_parking_user_review_notified",
                        audit_context=self.derive_audit_context(
                            _audit_context,
                            source_service="bot_service",
                            reason="guest_parking_user_review_notified",
                        ),
                        meta=self._build_delivery_meta(
                            delivery_channel="telegram_user",
                            target_chat_id=user_chat_id,
                            status="success",
                            extra={"status": status_value},
                        ),
                    )
                except Exception as send_error:
                    logger.exception(
                        "Failed to notify guest parking user request_id=%s user_id=%s: %s",
                        req_id,
                        user_id,
                        send_error,
                    )
                if notify_admin and target_chat_id is not None:
                    admin_text_key = (
                        "guest_parking_approved_admin"
                        if status_value == GuestParkingStatus.APPROVED
                        else "guest_parking_rejected_admin"
                    )
                    await self.bot.application.bot.send_message(
                        chat_id=target_chat_id,
                        text=self.bot.get_text(admin_text_key, [req_id]),
                        parse_mode=ParseMode.HTML,
                    )

            await self.edit_guest_parking_message(
                req_id=req_id,
                _audit_context=_audit_context,
                notify_admin_update=False,
            )
            return {"success": True, "error": None}
        except Exception as e:
            logger.exception("Failed to process guest parking review notification request_id=%s: %s", req_id, e)
            return {"success": False, "error": str(e)}

    async def delete_guest_parking_messages(self, req_id: int, _audit_context: Optional[dict] = None) -> Dict[str, Any]:
        """Удаляет сообщение заявки из чата администраторов. Вызывать перед удалением из БД."""
        try:
            resp = await self.bot.managers.database.guest_parking.get_by_id(entity_id=req_id)
            if not resp.get("success") or not resp.get("data"):
                return {"success": True, "error": None}
            touched_chat_ids = await self._delete_message_refs_with_messages(
                entity_type="GuestParkingRequest",
                entity_id=req_id,
            )
            if not touched_chat_ids:
                routed_chat_id = await self._resolve_guest_parking_chat_id(req_id=req_id)
                if routed_chat_id is not None:
                    touched_chat_ids = [routed_chat_id]
            admin_text = self.bot.get_text("guest_parking_deleted_admin", [req_id])
            for chat_id in touched_chat_ids:
                await self.bot.application.bot.send_message(
                    chat_id=chat_id,
                    text=admin_text,
                    parse_mode=ParseMode.HTML,
                )
            await self._append_delivery_audit_event(
                entity_type="GuestParkingRequest",
                entity_id=int(req_id),
                event_type="DELIVERY_DELETED",
                action="delete",
                reason="guest_parking_admin_chat_messages_deleted",
                audit_context=self.derive_audit_context(
                    _audit_context,
                    source_service="bot_service",
                    reason="guest_parking_admin_chat_messages_deleted",
                ),
                meta=self._build_delivery_meta(
                    delivery_channel="telegram_admin_chat",
                    status="success",
                    extra={"target_chat_ids": touched_chat_ids},
                ),
            )
            logger.info(
                "Deleted guest parking admin messages request_id=%s touched_chat_ids=%s",
                req_id,
                touched_chat_ids,
            )
            return {"success": True, "error": None}
        except Exception as e:
            await self._append_delivery_audit_event(
                entity_type="GuestParkingRequest",
                entity_id=int(req_id),
                event_type="DELIVERY_FAILED",
                action="delete",
                reason="guest_parking_admin_chat_message_delete_failed",
                audit_context=self.derive_audit_context(
                    _audit_context,
                    source_service="bot_service",
                    reason="guest_parking_admin_chat_message_delete_failed",
                ),
                meta=self._build_delivery_meta(
                    delivery_channel="telegram_admin_chat",
                    status="failed",
                    extra={"error": str(e)},
                ),
            )
            logger.exception("Failed to delete guest parking admin messages request_id=%s: %s", req_id, e)
            return {"success": False, "error": str(e)}

    async def is_admin_chat(self, chat_id: int) -> bool:
        """
        Checks if a given chat ID is the configured administrative chat.

        Args:
            chat_id: The chat ID to check.

        Returns:
            True if it is the admin chat, False otherwise.
        """
        return await self.bot.services.chat_routing.is_object_admin_chat(chat_id)
