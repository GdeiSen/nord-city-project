"""
API для заявок на гостевую парковку.
Синхронизация с чатом администраторов бота при создании/редактировании/удалении.
"""
import logging
from typing import Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from shared.clients.database_client import db_client
from shared.clients.bot_client import bot_client
from shared.constants import GuestParkingStatus
from shared.permissions import PermissionCodes
from shared.schemas.guest_parking import GuestParkingSchema
from shared.schemas.user import UserSchema
from api.dependencies import get_audit_context, get_current_user, require_permission
from api.schemas.common import MessageResponse, PaginatedResponse
from api.helpers.paginated_list import create_paginated_list_handler
from api.helpers.enrichment import enrich_guest_parking_with_users
from api.schemas.guest_parking import (
    GuestParkingResponse,
    CreateGuestParkingBody,
    UpdateGuestParkingBody,
    ReviewGuestParkingBody,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/guest-parking", tags=["Guest Parking"])


def _validate_interval(start_at, end_at) -> None:
    if start_at is None or end_at is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Укажите интервал заезда.")
    if end_at <= start_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Окончание интервала должно быть позже начала.")
    if (end_at - start_at).total_seconds() > 2 * 60 * 60:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Интервал парковки не может превышать 2 часа.")


@router.post("/", response_model=GuestParkingResponse, status_code=status.HTTP_201_CREATED)
async def create_guest_parking(
    body: CreateGuestParkingBody,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """Создать заявку на гостевую парковку. Синхронизирует с чатом администраторов."""
    audit_ctx = get_audit_context(request, current_user)
    data = body.model_dump()
    _validate_interval(data.get("arrival_start_at"), data.get("arrival_end_at"))
    data["arrival_date"] = data["arrival_start_at"]
    data["status"] = GuestParkingStatus.NEW
    if data.get("user_id") is not None:
        user_response = await db_client.user.get_by_id(
            entity_id=int(data["user_id"]),
            model_class=UserSchema,
        )
        user = user_response.get("data") if user_response.get("success") else None
        data["object_id"] = getattr(user, "object_id", None)
    response = await db_client.guest_parking.create(
        model_data=data,
        model_class=GuestParkingSchema,
        _audit_context=audit_ctx,
    )
    if not response.get("success"):
        error = response.get("error", "Failed to create guest parking request")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    schema = response.get("data")
    if not schema:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create")
    req_id = schema.id if hasattr(schema, "id") else schema.get("id")
    if req_id is not None:
        try:
            resp = await bot_client.notification.notify_new_guest_parking(req_id=req_id, _audit_context=audit_ctx)
            if resp and not resp.get("success"):
                logger.error(
                    "Bot notification for new guest parking failed: req_id=%s, error=%s",
                    req_id, resp.get("error", "unknown"),
                )
        except Exception as e:
            logger.error(
                "Bot notification for new guest parking failed: req_id=%s, error=%s",
                req_id, e, exc_info=True,
            )
    items = await enrich_guest_parking_with_users([schema])
    return items[0] if items else GuestParkingResponse.model_validate(schema)


get_guest_parking = create_paginated_list_handler(
    db_client.guest_parking,
    model_class=GuestParkingSchema,
    enricher=enrich_guest_parking_with_users,
    entity_label="guest parking requests",
)
router.get("/", response_model=PaginatedResponse[GuestParkingResponse])(
    get_guest_parking
)


@router.get("/{entity_id}", response_model=GuestParkingResponse)
async def get_guest_parking_by_id(entity_id: int):
    """Получить заявку на гостевую парковку по ID."""
    response = await db_client.guest_parking.get_by_id(
        entity_id=entity_id,
        model_class=GuestParkingSchema,
    )
    if not response.get("success"):
        error = response.get("error", "Guest parking request not found")
        code = status.HTTP_404_NOT_FOUND if "not found" in error.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=error)
    if response.get("data") is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guest parking request not found")
    items = await enrich_guest_parking_with_users([response["data"]])
    return items[0] if items else response["data"]


@router.put("/{entity_id}", response_model=MessageResponse)
async def update_guest_parking(
    entity_id: int,
    body: UpdateGuestParkingBody,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """Обновить заявку. Синхронизирует сообщение в чате администраторов."""
    audit_ctx = get_audit_context(request, current_user)
    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    old_resp = await db_client.guest_parking.get_by_id(entity_id=entity_id, model_class=GuestParkingSchema)
    old_req = old_resp.get("data") if old_resp.get("success") else None
    start_at = update_data.get("arrival_start_at", getattr(old_req, "arrival_start_at", None))
    end_at = update_data.get("arrival_end_at", getattr(old_req, "arrival_end_at", None))
    if "arrival_start_at" in update_data or "arrival_end_at" in update_data:
        _validate_interval(start_at, end_at)
        if "arrival_start_at" in update_data:
            update_data["arrival_date"] = update_data["arrival_start_at"]
    if update_data.get("user_id") is not None:
        user_response = await db_client.user.get_by_id(
            entity_id=int(update_data["user_id"]),
            model_class=UserSchema,
        )
        user = user_response.get("data") if user_response.get("success") else None
        update_data["object_id"] = getattr(user, "object_id", None)
    response = await db_client.guest_parking.update(
        entity_id=entity_id,
        update_data=update_data,
        _audit_context=audit_ctx,
    )
    if not response.get("success"):
        error = response.get("error", "Failed to update guest parking request")
        code = status.HTTP_404_NOT_FOUND if "not found" in error.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=error)
    try:
        resp = await bot_client.notification.edit_guest_parking_message(req_id=entity_id, _audit_context=audit_ctx)
        if resp and not resp.get("success"):
            logger.error(
                "Bot edit of guest parking message failed: entity_id=%s, error=%s",
                entity_id, resp.get("error", "unknown"),
            )
    except Exception as e:
        logger.error("Bot edit of guest parking message failed: entity_id=%s: %s", entity_id, e, exc_info=True)
    return MessageResponse(message="Guest parking request updated", id=entity_id)


async def _review_guest_parking(
    *,
    entity_id: int,
    status_value: str,
    body: ReviewGuestParkingBody,
    request: Request,
    current_user: dict,
) -> MessageResponse:
    require_permission(current_user, PermissionCodes.PARKING_APPROVE)
    audit_ctx = get_audit_context(request, current_user)
    update_data = {
        "status": status_value,
        "reviewed_by_user_id": int(current_user["user_id"]),
        "reviewed_at": datetime.now(timezone.utc),
        "rejection_reason": body.reason.strip() if body.reason and body.reason.strip() else None,
    }
    if status_value == GuestParkingStatus.REJECTED and not update_data["rejection_reason"]:
        update_data["rejection_reason"] = "Заявка отклонена администратором."
    response = await db_client.guest_parking.update(
        entity_id=entity_id,
        update_data=update_data,
        _audit_context=audit_ctx,
    )
    if not response.get("success"):
        error = response.get("error", "Failed to update guest parking request")
        code = status.HTTP_404_NOT_FOUND if "not found" in error.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=error)
    try:
        resp = await bot_client.notification.notify_guest_parking_reviewed(req_id=entity_id, _audit_context=audit_ctx)
        if resp and not resp.get("success"):
            logger.error("Bot guest parking review notification failed: entity_id=%s, error=%s", entity_id, resp.get("error"))
    except Exception as e:
        logger.error("Bot guest parking review notification failed: entity_id=%s: %s", entity_id, e, exc_info=True)
    return MessageResponse(message="Guest parking request reviewed", id=entity_id)


@router.post("/{entity_id}/approve", response_model=MessageResponse)
async def approve_guest_parking(
    entity_id: int,
    body: ReviewGuestParkingBody,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    return await _review_guest_parking(
        entity_id=entity_id,
        status_value=GuestParkingStatus.APPROVED,
        body=body,
        request=request,
        current_user=current_user,
    )


@router.post("/{entity_id}/reject", response_model=MessageResponse)
async def reject_guest_parking(
    entity_id: int,
    body: ReviewGuestParkingBody,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    return await _review_guest_parking(
        entity_id=entity_id,
        status_value=GuestParkingStatus.REJECTED,
        body=body,
        request=request,
        current_user=current_user,
    )


@router.delete("/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_guest_parking(
    entity_id: int,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """Удалить заявку. Сначала удаляет сообщение из чата администраторов."""
    audit_ctx = get_audit_context(request, current_user)
    try:
        resp = await bot_client.notification.delete_guest_parking_messages(req_id=entity_id, _audit_context=audit_ctx)
        if resp and not resp.get("success", True):
            logger.error(
                "Bot deletion of guest parking message failed: entity_id=%s, error=%s",
                entity_id, resp.get("error", "unknown"),
            )
    except Exception as e:
        logger.error("Bot deletion of guest parking message failed: entity_id=%s: %s", entity_id, e, exc_info=True)
    response = await db_client.guest_parking.delete(
        entity_id=entity_id,
        _audit_context=audit_ctx,
    )
    if not response.get("success"):
        error = response.get("error", "Failed to delete guest parking request")
        code = status.HTTP_404_NOT_FOUND if "not found" in error.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=error)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
