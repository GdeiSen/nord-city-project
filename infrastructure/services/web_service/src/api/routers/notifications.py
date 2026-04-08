import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status

from api.dependencies import get_audit_context, get_current_user
from api.schemas.notifications import (
    NotificationBroadcastRequest,
    NotificationBroadcastResponse,
)
from shared.clients.bot_client import bot_client
from shared.clients.database_client import db_client
from shared.clients.storage_client import storage_client
from shared.constants import Roles, StorageFileCategory
from shared.schemas.storage_file import StorageFileSchema
from shared.schemas.user import UserSchema
from shared.utils.storage_utils import STORAGE_PATH_PATTERN, extract_storage_path

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


def _require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """Ensure user is Admin or Super Admin."""
    role = current_user.get("role")
    if role not in (Roles.ADMIN, Roles.SUPER_ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ только для администраторов.",
        )
    return current_user


def _resolve_storage_path(raw_value: str) -> str | None:
    candidate = str(raw_value or "").strip()
    if not candidate:
        return None

    storage_path = extract_storage_path(candidate)
    if storage_path is not None:
        return storage_path

    fallback_path = candidate.lstrip("/")
    if fallback_path.startswith("storage/"):
        fallback_path = fallback_path[8:].lstrip("/")
    if fallback_path and STORAGE_PATH_PATTERN.match(fallback_path):
        return fallback_path

    return None


def _normalize_attachment_urls(attachment_urls: list[str]) -> tuple[list[str], list[str]]:
    """Accept only storage files and return both public URLs and canonical storage paths."""
    normalized_urls: list[str] = []
    normalized_paths: list[str] = []
    seen_paths: set[str] = set()

    for raw_url in attachment_urls or []:
        if not str(raw_url or "").strip():
            continue
        storage_path = _resolve_storage_path(raw_url)
        if storage_path is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Можно прикреплять только файлы, загруженные через storage service.",
            )

        if storage_path in seen_paths:
            continue
        seen_paths.add(storage_path)
        normalized_paths.append(storage_path)
        normalized_urls.append(storage_client.get_storage_url(storage_path))

    return normalized_urls, normalized_paths


async def _cleanup_temp_notification_attachments(
    storage_paths: list[str],
    *,
    audit_context: dict | None = None,
) -> None:
    """
    Remove only TEMP files created for notification delivery.
    Bound files and non-TEMP categories are left untouched.
    """
    for path in storage_paths:
        try:
            lookup = await db_client.storage_file.find_by_path(
                storage_path=path,
                model_class=StorageFileSchema,
            )
            if not lookup.get("success"):
                logger.warning(
                    "Failed to lookup storage file for notification cleanup: path=%s, error=%s",
                    path,
                    lookup.get("error"),
                )
                continue

            file_item = lookup.get("data")
            if file_item is None:
                continue
            if file_item.category != StorageFileCategory.TEMP:
                continue
            if file_item.entity_type or file_item.entity_id is not None:
                continue

            delete_response = await db_client.storage_file.delete_file(
                storage_path=path,
                remove_reference=False,
                _audit_context=audit_context,
            )
            if not delete_response.get("success"):
                logger.warning(
                    "Failed to cleanup temp notification attachment: path=%s, error=%s",
                    path,
                    delete_response.get("error"),
                )
        except Exception as exc:
            logger.warning(
                "Unexpected error during notification attachment cleanup for %s: %s",
                path,
                exc,
            )


def _extract_user_id(user: UserSchema | dict) -> int | None:
    if isinstance(user, dict):
        value = user.get("id")
    else:
        value = getattr(user, "id", None)
    return int(value) if value is not None else None


@router.post("/broadcast", response_model=NotificationBroadcastResponse)
async def broadcast_notification(
    body: NotificationBroadcastRequest,
    request: Request,
    current_user: dict = Depends(_require_admin),
):
    attachment_urls, attachment_paths = _normalize_attachment_urls(body.attachment_urls or body.image_urls)

    recipient_response = await db_client.user.get_notification_recipients(
        role_ids=body.role_ids,
        user_ids=body.user_ids,
        model_class=UserSchema,
    )
    if not recipient_response.get("success"):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=recipient_response.get("error", "Не удалось определить получателей."),
        )

    recipients = recipient_response.get("data") or []
    recipient_ids = sorted(
        {
            user_id
            for user_id in (_extract_user_id(user) for user in recipients)
            if user_id is not None
        }
    )
    if not recipient_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="По выбранным фильтрам не найдено ни одного получателя.",
        )

    audit_context = get_audit_context(request, current_user)
    bot_response = await bot_client.notification.send_bulk_notification(
        user_ids=recipient_ids,
        title=body.title,
        message=body.message,
        attachment_urls=attachment_urls,
        _audit_context=audit_context,
    )
    if not bot_response.get("success"):
        error = bot_response.get("error", "Не удалось отправить уведомление.")
        status_code = (
            status.HTTP_400_BAD_REQUEST
            if error in {"no_recipients", "empty_message"}
            else status.HTTP_502_BAD_GATEWAY
        )
        raise HTTPException(status_code=status_code, detail=error)

    if attachment_paths:
        await _cleanup_temp_notification_attachments(
            attachment_paths,
            audit_context=audit_context,
        )

    delivery_data = bot_response.get("data") or {}
    failed_deliveries = delivery_data.get("failed_deliveries") or []
    failed_user_ids = [
        int(item.get("user_id"))
        for item in failed_deliveries
        if isinstance(item, dict) and item.get("user_id") is not None
    ]

    if failed_user_ids:
        logger.warning(
            "Bulk notification finished with failed deliveries: user_ids=%s",
            failed_user_ids,
        )

    return NotificationBroadcastResponse(
        resolved_recipient_count=len(recipient_ids),
        sent_count=int(delivery_data.get("sent_count", 0)),
        failed_count=int(delivery_data.get("failed_count", len(failed_user_ids))),
        failed_user_ids=failed_user_ids,
    )
