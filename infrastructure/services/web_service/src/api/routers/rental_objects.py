import logging
from typing import List

from fastapi import APIRouter, HTTPException, Response, status

from shared.clients.database_client import db_client
from api.schemas.common import MessageResponse
from api.schemas.rental_objects import ObjectResponse, CreateObjectRequest, UpdateObjectBody

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/rental-objects", tags=["Rental Objects"])


@router.post("/", response_model=ObjectResponse, status_code=status.HTTP_201_CREATED)
async def create_object(body: CreateObjectRequest):
    response = await db_client.object.create(model_data=body.model_dump())
    if not response.get("success"):
        error = response.get("error", "Failed to create rental object")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return response["data"]


@router.get("/", response_model=List[ObjectResponse])
async def get_all_objects():
    response = await db_client.object.get_all()
    if not response.get("success"):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=response.get("error", "Failed to fetch rental objects"))
    return response.get("data", [])


@router.get("/{entity_id}", response_model=ObjectResponse)
async def get_object_by_id(entity_id: int):
    response = await db_client.object.get_by_id(entity_id=entity_id)
    if not response.get("success"):
        error = response.get("error", "Rental object not found")
        code = status.HTTP_404_NOT_FOUND if "not found" in error.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=error)
    if response.get("data") is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rental object not found")
    return response["data"]


@router.put("/{entity_id}", response_model=MessageResponse)
async def update_object(entity_id: int, body: UpdateObjectBody):
    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    response = await db_client.object.update(entity_id=entity_id, update_data=update_data)
    if not response.get("success"):
        error = response.get("error", "Failed to update rental object")
        code = status.HTTP_404_NOT_FOUND if "not found" in error.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=error)
    return MessageResponse(message="Rental object updated successfully", id=entity_id)


@router.delete("/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_object(entity_id: int):
    response = await db_client.object.delete(entity_id=entity_id)
    if not response.get("success"):
        error = response.get("error", "Failed to delete rental object")
        code = status.HTTP_404_NOT_FOUND if "not found" in error.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=error)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
