import logging
from typing import List

from fastapi import APIRouter, HTTPException, Response, status

from shared.clients.database_client import db_client
from api.schemas.common import MessageResponse
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


@router.get("/", response_model=List[ServiceTicketResponse])
async def get_all_service_tickets():
    response = await db_client.service_ticket.get_all()
    if not response.get("success"):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=response.get("error", "Failed to fetch service tickets"))
    return response.get("data", [])


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
