"""
API для заявок на гостевую парковку.
Синхронизация с чатом администраторов бота при создании/редактировании/удалении.
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Response, status

from shared.clients.database_client import db_client
from shared.clients.bot_client import bot_client
from shared.schemas.guest_parking import GuestParkingSchema
from api.dependencies import get_audit_context, get_optional_current_user
from api.schemas.common import MessageResponse, PaginatedResponse
from api.helpers.paginated_list import create_paginated_list_handler
from api.helpers.enrichment import enrich_guest_parking_with_users
from api.schemas.guest_parking import (
    GuestParkingResponse,
    CreateGuestParkingBody,
    UpdateGuestParkingBody,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/guest-parking", tags=["Guest Parking"])


@router.post("/", response_model=GuestParkingResponse, status_code=status.HTTP_201_CREATED)
async def create_guest_parking(body: CreateGuestParkingBody, request: Request):
    """Создать заявку на гостевую парковку. Синхронизирует с чатом администраторов."""
    data = body.model_dump()
    response = await db_client.guest_parking.create(
        model_data=data,
        model_class=GuestParkingSchema,
        _audit_context=get_audit_context(request, get_optional_current_user(request)),
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
            await bot_client.notification.notify_new_guest_parking(req_id=req_id)
        except Exception as e:
            logger.warning("Bot notification for new guest parking failed: %s", e)
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
async def update_guest_parking(entity_id: int, body: UpdateGuestParkingBody, request: Request):
    """Обновить заявку. Синхронизирует сообщение в чате администраторов."""
    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    response = await db_client.guest_parking.update(
        entity_id=entity_id,
        update_data=update_data,
        _audit_context=get_audit_context(request, get_optional_current_user(request)),
    )
    if not response.get("success"):
        error = response.get("error", "Failed to update guest parking request")
        code = status.HTTP_404_NOT_FOUND if "not found" in error.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=error)
    try:
        await bot_client.notification.edit_guest_parking_message(req_id=entity_id)
    except Exception as e:
        logger.warning("Bot edit of guest parking message failed: %s", e)
    return MessageResponse(message="Guest parking request updated", id=entity_id)


@router.delete("/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_guest_parking(entity_id: int, request: Request):
    """Удалить заявку. Сначала удаляет сообщение из чата администраторов."""
    try:
        await bot_client.notification.delete_guest_parking_messages(req_id=entity_id)
    except Exception as e:
        logger.warning("Bot deletion of guest parking message failed: %s", e)
    response = await db_client.guest_parking.delete(
        entity_id=entity_id,
        _audit_context=get_audit_context(request, get_optional_current_user(request)),
    )
    if not response.get("success"):
        error = response.get("error", "Failed to delete guest parking request")
        code = status.HTTP_404_NOT_FOUND if "not found" in error.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=error)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
