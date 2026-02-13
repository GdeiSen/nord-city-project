import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Response, status

from shared.clients.database_client import db_client
from api.schemas.common import MessageResponse, PaginatedResponse, parse_sort_param
from api.schemas.service_tickets import (
    ServiceTicketResponse,
    CreateServiceTicketRequest,
    UpdateServiceTicketBody,
    ServiceTicketsStatsResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/service-tickets", tags=["Service Tickets"])


@router.post("/", response_model=ServiceTicketResponse, status_code=status.HTTP_201_CREATED)
async def create_service_ticket(body: CreateServiceTicketRequest):
    response = await db_client.service_ticket.create(model_data=body.model_dump())
    if not response.get("success"):
        error = response.get("error", "Failed to create service ticket")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return response["data"]


@router.get("/stats", response_model=ServiceTicketsStatsResponse)
async def get_service_tickets_stats():
    """Must be registered BEFORE /{entity_id} to avoid path conflict."""
    response = await db_client.service_ticket.get_stats()
    if not response.get("success"):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=response.get("error", "Failed to get stats"))
    return response["data"]


@router.get("/", response_model=PaginatedResponse[ServiceTicketResponse])
async def get_service_tickets(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=500),
    search: Optional[str] = None,
    sort: Optional[str] = None,
    search_columns: Optional[str] = None,
):
    cols = [c.strip() for c in (search_columns or "").split(",") if c.strip()]
    response = await db_client.service_ticket.get_paginated(
        page=page,
        page_size=page_size,
        sort=parse_sort_param(sort),
        search=search or "",
        search_columns=cols if cols else None,
    )
    if not response.get("success"):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=response.get("error", "Failed to fetch service tickets"))
    data = response.get("data", {})
    items = data.get("items", [])
    # Enrich with user data
    user_ids = list({t.get("user_id") for t in items if t.get("user_id")})
    user_map = {}
    for uid in user_ids:
        try:
            ur = await db_client.user.get_by_id(entity_id=uid)
            if ur.get("success") and ur.get("data"):
                user_map[uid] = ur["data"]
        except Exception:
            pass
    # Enrich with object (business center) from user's object_id - batch fetch for reliable names
    object_ids = set(u.get("object_id") for u in user_map.values() if u.get("object_id"))
    object_map = {}
    if object_ids:
        try:
            page, page_size = 1, 100
            while object_ids - object_map.keys():
                obj_resp = await db_client.object.get_paginated(
                    page=page, page_size=page_size
                )
                if not obj_resp.get("success"):
                    break
                data = obj_resp.get("data", {})
                objs = data.get("items", [])
                if not objs:
                    break
                for obj in objs:
                    oid = obj.get("id")
                    if oid in object_ids and oid not in object_map:
                        name = obj.get("name") or (f"БЦ-{oid}" if oid else "")
                        object_map[oid] = {"id": oid, "name": name}
                total = data.get("total", 0)
                if page * page_size >= total:
                    break
                page += 1
        except Exception as e:
            logger.warning("Failed to batch-fetch objects for enrichment: %s", e)
    for t in items:
        u = user_map.get(t.get("user_id"), {"first_name": "Unknown", "last_name": "", "username": ""})
        t["user"] = u
        oid = u.get("object_id")
        t["object"] = object_map.get(oid) if oid else None
    return PaginatedResponse(items=items, total=data.get("total", 0))


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
async def update_service_ticket(entity_id: int, body: UpdateServiceTicketBody):
    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    response = await db_client.service_ticket.update(entity_id=entity_id, update_data=update_data)
    if not response.get("success"):
        error = response.get("error", "Failed to update service ticket")
        code = status.HTTP_404_NOT_FOUND if "not found" in error.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=error)
    return MessageResponse(message="Service ticket updated successfully", id=entity_id)


@router.delete("/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_service_ticket(entity_id: int):
    response = await db_client.service_ticket.delete(entity_id=entity_id)
    if not response.get("success"):
        error = response.get("error", "Failed to delete service ticket")
        code = status.HTTP_404_NOT_FOUND if "not found" in error.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=error)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
