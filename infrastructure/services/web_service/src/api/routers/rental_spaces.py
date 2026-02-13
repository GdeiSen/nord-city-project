import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Response, status

from shared.clients.database_client import db_client
from api.schemas.common import MessageResponse, PaginatedResponse, parse_sort_param
from api.schemas.rental_spaces import SpaceResponse, CreateSpaceRequest, UpdateSpaceBody

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/rental-spaces", tags=["Rental Spaces"])


@router.post("/", response_model=SpaceResponse, status_code=status.HTTP_201_CREATED)
async def create_space(body: CreateSpaceRequest):
    response = await db_client.space.create(model_data=body.model_dump())
    if not response.get("success"):
        error = response.get("error", "Failed to create rental space")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return response["data"]


@router.get("/", response_model=PaginatedResponse[SpaceResponse])
async def get_spaces(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=500),
    search: Optional[str] = None,
    sort: Optional[str] = None,
    object_id: Optional[int] = None,
):
    filters = [{"columnId": "object_id", "operator": "equals", "value": str(object_id)}] if object_id else []
    response = await db_client.space.get_paginated(
        page=page,
        page_size=page_size,
        sort=parse_sort_param(sort),
        filters=filters if filters else None,
        search=search or "",
        search_columns=["floor", "description", "status"],
    )
    if not response.get("success"):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=response.get("error", "Failed to fetch rental spaces"))
    data = response.get("data", {})
    return PaginatedResponse(items=data.get("items", []), total=data.get("total", 0))


@router.get("/rental-objects/{object_id}", response_model=List[SpaceResponse])
async def get_spaces_by_object_id(object_id: int):
    """Must be registered BEFORE /{entity_id} to avoid path conflict."""
    response = await db_client.space.find(filters={"object_id": object_id})
    if not response.get("success"):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=response.get("error", "Failed to find rental spaces"))
    return response.get("data", [])


@router.get("/{entity_id}", response_model=SpaceResponse)
async def get_space_by_id(entity_id: int):
    response = await db_client.space.get_by_id(entity_id=entity_id)
    if not response.get("success"):
        error = response.get("error", "Rental space not found")
        code = status.HTTP_404_NOT_FOUND if "not found" in error.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=error)
    if response.get("data") is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rental space not found")
    return response["data"]


@router.put("/{entity_id}", response_model=MessageResponse)
async def update_space(entity_id: int, body: UpdateSpaceBody):
    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    response = await db_client.space.update(entity_id=entity_id, update_data=update_data)
    if not response.get("success"):
        error = response.get("error", "Failed to update rental space")
        code = status.HTTP_404_NOT_FOUND if "not found" in error.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=error)
    return MessageResponse(message="Rental space updated successfully", id=entity_id)


@router.delete("/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_space(entity_id: int):
    response = await db_client.space.delete(entity_id=entity_id)
    if not response.get("success"):
        error = response.get("error", "Failed to delete rental space")
        code = status.HTTP_404_NOT_FOUND if "not found" in error.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=error)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
