from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_current_user
from api.schemas.guest_parking_settings import (
    GuestParkingSettingsResponse,
    UpdateGuestParkingSettingsBody,
)
from shared.clients.database_client import db_client
from shared.clients.media_client import media_client
from shared.constants import Roles
from shared.schemas.guest_parking_settings import GuestParkingSettingsSchema
from shared.utils.media_utils import MEDIA_PATH_PATTERN, extract_media_path

router = APIRouter(prefix="/guest-parking-settings", tags=["Guest Parking Settings"])


def _require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    role = current_user.get("role")
    if role not in (Roles.ADMIN, Roles.SUPER_ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ только для администраторов.",
        )
    return current_user


def _normalize_route_images(route_images: list[str]) -> list[str]:
    normalized: list[str] = []
    seen_paths: set[str] = set()

    for raw_url in route_images or []:
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
                detail="Можно использовать только изображения, загруженные в media service.",
            )
        lower_path = media_path.lower()
        if not lower_path.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Для схемы проезда допускаются только изображения (JPG, PNG, GIF, WebP).",
            )
        if media_path in seen_paths:
            continue
        seen_paths.add(media_path)
        normalized.append(media_client.get_media_url(media_path))

    return normalized[:2]


@router.get("/", response_model=GuestParkingSettingsResponse)
async def get_guest_parking_settings(_: dict = Depends(_require_admin)):
    response = await db_client.guest_parking_settings.get_settings(model_class=GuestParkingSettingsSchema)
    if not response.get("success"):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=response.get("error", "Не удалось загрузить настройки."),
        )
    settings = response.get("data") or GuestParkingSettingsSchema(id=1, route_images=[])
    if isinstance(settings, dict):
        return GuestParkingSettingsResponse(**settings)
    return GuestParkingSettingsResponse(**settings.model_dump())


@router.put("/", response_model=GuestParkingSettingsResponse)
async def update_guest_parking_settings(
    body: UpdateGuestParkingSettingsBody,
    current_user: dict = Depends(_require_admin),
):
    response = await db_client.guest_parking_settings.save_settings(
        route_images=_normalize_route_images(body.route_images),
        model_class=GuestParkingSettingsSchema,
        _audit_context={"source": "web_service", "assignee_id": current_user["user_id"]},
    )
    if not response.get("success"):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=response.get("error", "Не удалось сохранить настройки."),
        )
    settings = response.get("data")
    if isinstance(settings, dict):
        return GuestParkingSettingsResponse(**settings)
    return GuestParkingSettingsResponse(**settings.model_dump())
