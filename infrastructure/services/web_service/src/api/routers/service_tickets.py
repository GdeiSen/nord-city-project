import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Request, Response, status

from shared.clients.database_client import db_client
from shared.clients.bot_client import bot_client
from shared.constants import ServiceTicketStatus
from api.dependencies import get_audit_context, get_optional_current_user
from api.schemas.common import MessageResponse, PaginatedResponse, parse_sort_param
from api.schemas.list_params import parse_list_params_from_query
from api.helpers.paginated_list import create_paginated_list_handler
from api.helpers.enrichment import enrich_service_tickets_with_users_and_objects
from api.helpers.export_csv import build_csv
from api.schemas.service_tickets import (
    ServiceTicketResponse,
    CreateServiceTicketRequest,
    UpdateServiceTicketBody,
    ServiceTicketsStatsResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/service-tickets", tags=["Service Tickets"])

EXPORT_MAX_LIMIT = 10_000
SERVICE_TICKET_EXPORT_HEADERS = {
    "id": "ID",
    "ticket": "Заявка",
    "user": "Пользователь",
    "object": "Объект",
    "status": "Статус",
    "created": "Создана",
}


def _get_ticket_export_value(col_id: str):
    def getter(item: dict):
        if col_id == "id":
            return str(item.get("id", ""))
        if col_id == "ticket":
            desc = item.get("description") or ""
            loc = item.get("location") or ""
            return f"{desc} | {loc}".strip(" |") if (desc or loc) else ""
        if col_id == "user":
            u = item.get("user") or {}
            parts = [u.get("last_name"), u.get("first_name"), u.get("middle_name")]
            name = " ".join(p or "" for p in parts).strip()
            un = u.get("username", "")
            return f"{name} @{un}".strip(" @") if (name or un) else ""
        if col_id == "object":
            o = item.get("object")
            return o.get("name", f"БЦ-{o.get('id', '')}") if o else ""
        if col_id == "status":
            return item.get("status", "")
        if col_id == "created":
            return item.get("created_at", "")
        return str(item.get(col_id, ""))

    return getter


@router.post("/", response_model=ServiceTicketResponse, status_code=status.HTTP_201_CREATED)
async def create_service_ticket(body: CreateServiceTicketRequest, request: Request):
    data = body.model_dump()
    data["status"] = ServiceTicketStatus.NEW  # Always NEW for new tickets
    response = await db_client.service_ticket.create(
        model_data=data,
        _audit_context=get_audit_context(request, get_optional_current_user(request)),
    )
    if not response.get("success"):
        error = response.get("error", "Failed to create service ticket")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    ticket_data = response["data"]
    ticket_id = ticket_data.get("id") if isinstance(ticket_data, dict) else getattr(ticket_data, "id", None)
    if ticket_id is not None:
        try:
            await bot_client.notification.notify_new_ticket(ticket_id=ticket_id)
        except Exception as e:
            logger.warning("Bot notification for new ticket failed: %s", e)
    return ticket_data


@router.get("/stats", response_model=ServiceTicketsStatsResponse)
async def get_service_tickets_stats():
    """Must be registered BEFORE /{entity_id} to avoid path conflict."""
    response = await db_client.service_ticket.get_stats()
    if not response.get("success"):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=response.get("error", "Failed to get stats"))
    return response["data"]


get_service_tickets = create_paginated_list_handler(
    db_client.service_ticket,
    enricher=enrich_service_tickets_with_users_and_objects,
    entity_label="service tickets",
)
router.get("/", response_model=PaginatedResponse[ServiceTicketResponse])(get_service_tickets)


@router.get("/export")
async def export_service_tickets(
    search: Optional[str] = None,
    sort: Optional[str] = None,
    search_columns: Optional[str] = None,
    filters: Optional[str] = None,
    columns: Optional[str] = None,
    limit: int = Query(1000, ge=1, le=EXPORT_MAX_LIMIT),
):
    """Export service tickets as CSV. Uses current filters, sort, search. Limited to EXPORT_MAX_LIMIT rows."""
    page, page_size, search_val, sort_val, cols, filter_list = parse_list_params_from_query(
        page=1,
        page_size=limit,
        search=search,
        sort=sort,
        search_columns=search_columns,
        filters=filters,
        max_page_size=None,
    )
    column_ids = [c.strip() for c in (columns or "id,ticket,user,object,status,created").split(",") if c.strip()]
    column_ids = [c for c in column_ids if c in SERVICE_TICKET_EXPORT_HEADERS] or list(SERVICE_TICKET_EXPORT_HEADERS)
    response = await db_client.service_ticket.get_paginated(
        page=page,
        page_size=page_size,
        sort=parse_sort_param(sort_val),
        search=search_val,
        search_columns=cols,
        filters=filter_list,
    )
    if not response.get("success"):
        raise HTTPException(status_code=500, detail=response.get("error", "Export failed"))
    data = response.get("data", {})
    items = data.get("items", [])
    await enrich_service_tickets_with_users_and_objects(items)
    value_getters = {c: _get_ticket_export_value(c) for c in column_ids}
    csv_content = build_csv(items, column_ids, value_getters, SERVICE_TICKET_EXPORT_HEADERS)
    utf8_bom = "\ufeff"
    body = (utf8_bom + csv_content).encode("utf-8")
    return Response(
        content=body,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="service-tickets.csv"'},
    )


@router.get("/msid/{msid}", response_model=List[ServiceTicketResponse])
async def get_service_tickets_by_msid(msid: int):
    """Must be registered BEFORE /{entity_id} to avoid path conflict."""
    response = await db_client.service_ticket.find(filters={"msid": msid})
    if not response.get("success"):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=response.get("error", "Failed to find service tickets"))
    return response.get("data", [])


@router.get("/{entity_id}", response_model=ServiceTicketResponse)
async def get_service_ticket_by_id(entity_id: int):
    response = await db_client.service_ticket.get_by_id(entity_id=entity_id)
    if not response.get("success"):
        error = response.get("error", "Service ticket not found")
        code = status.HTTP_404_NOT_FOUND if "not found" in error.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=error)
    if response.get("data") is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service ticket not found")
    return response["data"]


@router.put("/{entity_id}", response_model=MessageResponse)
async def update_service_ticket(entity_id: int, body: UpdateServiceTicketBody, request: Request):
    update_data = body.model_dump(exclude_unset=True)
    assignee_id_for_meta = update_data.pop("assignee_id", None)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    # Получаем старый статус до обновления — уведомление "заявка выполнена" только при смене на COMPLETED
    old_resp = await db_client.service_ticket.get_by_id(entity_id=entity_id)
    old_ticket = old_resp.get("data") if old_resp.get("success") else None
    old_status = old_ticket.get("status") if isinstance(old_ticket, dict) else (getattr(old_ticket, "status", None) if old_ticket else None)
    new_status = update_data.get("status")
    # Уведомление "заявка выполнена" — только когда статус реально сменился на COMPLETED
    status_changed_to_completed = (
        new_status == ServiceTicketStatus.COMPLETED
        and old_ticket is not None
        and old_status != ServiceTicketStatus.COMPLETED
    )
    audit_ctx = get_audit_context(request, get_optional_current_user(request))
    if update_data.get("status") == ServiceTicketStatus.ASSIGNED and assignee_id_for_meta is not None:
        audit_ctx["meta"] = audit_ctx.get("meta") or {}
        if isinstance(audit_ctx["meta"], dict):
            audit_ctx["meta"] = dict(audit_ctx["meta"])
        audit_ctx["meta"]["assignee_id"] = assignee_id_for_meta
    response = await db_client.service_ticket.update(
        entity_id=entity_id,
        update_data=update_data,
        _audit_context=audit_ctx,
    )
    if not response.get("success"):
        error = response.get("error", "Failed to update service ticket")
        code = status.HTTP_404_NOT_FOUND if "not found" in error.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=error)
    if not status_changed_to_completed:
        try:
            await bot_client.notification.edit_ticket_message(ticket_id=entity_id)
        except Exception as e:
            logger.warning("Bot edit of ticket message failed: %s", e)
    if status_changed_to_completed:
        try:
            await bot_client.notification.notify_ticket_completion(ticket_id=entity_id)
        except Exception as e:
            logger.warning("Bot notification for ticket completion failed: %s", e)
    return MessageResponse(message="Service ticket updated successfully", id=entity_id)


@router.delete("/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_service_ticket(entity_id: int, request: Request):
    try:
        await bot_client.notification.delete_ticket_messages(ticket_id=entity_id)
    except Exception as e:
        logger.warning("Bot deletion of ticket messages failed: %s", e)
    response = await db_client.service_ticket.delete(
        entity_id=entity_id,
        _audit_context=get_audit_context(request, get_optional_current_user(request)),
    )
    if not response.get("success"):
        error = response.get("error", "Failed to delete service ticket")
        code = status.HTTP_404_NOT_FOUND if "not found" in error.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=error)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
