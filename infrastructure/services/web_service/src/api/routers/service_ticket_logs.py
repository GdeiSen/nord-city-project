import logging
from typing import List

from fastapi import APIRouter, HTTPException, Response, status

from shared.clients.database_client import db_client
from api.schemas.common import MessageResponse
from api.schemas.service_ticket_logs import ServiceTicketLogResponse, CreateLogRequest, UpdateLogBody

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/service-ticket-logs", tags=["Service Ticket Logs"])


@router.post("/", response_model=ServiceTicketLogResponse, status_code=status.HTTP_201_CREATED)
async def create_log(body: CreateLogRequest):
    response = await db_client.service_ticket_log.create(model_data=body.model_dump())
    if not response.get("success"):
        error = response.get("error", "Failed to create log entry")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return response["data"]


@router.get("/", response_model=List[ServiceTicketLogResponse])
async def get_all_logs():
    response = await db_client.service_ticket_log.get_all()
    if not response.get("success"):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=response.get("error", "Failed to fetch logs"))
    return response.get("data", [])


@router.get("/{entity_id}", response_model=ServiceTicketLogResponse)
async def get_log_by_id(entity_id: int):
    response = await db_client.service_ticket_log.get_by_id(entity_id=entity_id)
    if not response.get("success"):
        error = response.get("error", "Log entry not found")
        code = status.HTTP_404_NOT_FOUND if "not found" in error.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=error)
    if response.get("data") is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Log entry not found")
    return response["data"]


@router.put("/{entity_id}", response_model=MessageResponse)
async def update_log(entity_id: int, body: UpdateLogBody):
    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    response = await db_client.service_ticket_log.update(entity_id=entity_id, update_data=update_data)
    if not response.get("success"):
        error = response.get("error", "Failed to update log entry")
        code = status.HTTP_404_NOT_FOUND if "not found" in error.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=error)
    return MessageResponse(message="Log entry updated successfully", id=entity_id)


@router.delete("/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_log(entity_id: int):
    response = await db_client.service_ticket_log.delete(entity_id=entity_id)
    if not response.get("success"):
        error = response.get("error", "Failed to delete log entry")
        code = status.HTTP_404_NOT_FOUND if "not found" in error.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=error)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
