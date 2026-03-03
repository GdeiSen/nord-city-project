import logging

from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_current_user
from api.schemas.notifications import (
    NotificationBroadcastRequest,
    NotificationBroadcastResponse,
)
from shared.clients.bot_client import bot_client
from shared.clients.database_client import db_client
from shared.clients.media_client import media_client
from shared.constants import Roles
from shared.schemas.user import UserSchema
from shared.utils.media_utils import MEDIA_PATH_PATTERN, extract_media_path

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


def _normalize_attachment_urls(attachment_urls: list[str]) -> list[str]:
    """Accept only files stored in our storage service and convert them to public URLs."""
    normalized_urls: list[str] = []
    seen_paths: set[str] = set()

    for raw_url in attachment_urls or []:
        candidate = str(raw_url or "").strip()
        if not candidate:
            continue

        media_path = extract_media_path(candidate)
        if media_path is None:
            fallback_path = candidate.lstrip("/")
            if fallback_path.startswith("media/"):
                fallback_path = fallback_path[6:].lstrip("/")
            if fallback_path and MEDIA_PATH_PATTERN.match(fallback_path):
                media_path = fallback_path

        if media_path is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Можно прикреплять только файлы, загруженные через storage service.",
            )

        if media_path in seen_paths:
            continue
        seen_paths.add(media_path)
        normalized_urls.append(media_client.get_media_url(media_path))

    return normalized_urls


def _extract_user_id(user: UserSchema | dict) -> int | None:
    if isinstance(user, dict):
        value = user.get("id")
    else:
        value = getattr(user, "id", None)
    return int(value) if value is not None else None


@router.post("/broadcast", response_model=NotificationBroadcastResponse)
async def broadcast_notification(
    body: NotificationBroadcastRequest,
    _: dict = Depends(_require_admin),
):
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

    bot_response = await bot_client.notification.send_bulk_notification(
        user_ids=recipient_ids,
        title=body.title,
        message=body.message,
        attachment_urls=_normalize_attachment_urls(body.attachment_urls or body.image_urls),
    )
    if not bot_response.get("success"):
        error = bot_response.get("error", "Не удалось отправить уведомление.")
        status_code = (
            status.HTTP_400_BAD_REQUEST
            if error in {"no_recipients", "empty_message"}
            else status.HTTP_502_BAD_GATEWAY
        )
        raise HTTPException(status_code=status_code, detail=error)

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
