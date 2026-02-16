import logging
from typing import List

from fastapi import APIRouter, HTTPException, Response, status

from shared.clients.database_client import db_client
from api.schemas.common import MessageResponse
from api.schemas.space_views import SpaceViewResponse, CreateSpaceViewRequest, UpdateSpaceViewBody

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/space-views", tags=["Space Views"])


@router.post("/", response_model=SpaceViewResponse, status_code=status.HTTP_201_CREATED)
async def create_space_view(body: CreateSpaceViewRequest):
    response = await db_client.space_view.create(model_data=body.model_dump())
    if not response.get("success"):
        error = response.get("error", "Failed to create space view")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return response["data"]


@router.get("/", response_model=List[SpaceViewResponse])
async def get_all_space_views():
    response = await db_client.space_view.get_all()
    if not response.get("success"):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=response.get("error", "Failed to fetch space views"))
    return response.get("data", [])


@router.get("/{entity_id}", response_model=SpaceViewResponse)
async def get_space_view_by_id(entity_id: int):
    response = await db_client.space_view.get_by_id(entity_id=entity_id)
    if not response.get("success"):
        error = response.get("error", "Space view not found")
        code = status.HTTP_404_NOT_FOUND if "not found" in error.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=error)
    if response.get("data") is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Space view not found")
    return response["data"]


@router.put("/{entity_id}", response_model=MessageResponse)
async def update_space_view(entity_id: int, body: UpdateSpaceViewBody):
    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    response = await db_client.space_view.update(entity_id=entity_id, update_data=update_data)
    if not response.get("success"):
        error = response.get("error", "Failed to update space view")
        code = status.HTTP_404_NOT_FOUND if "not found" in error.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=error)
    return MessageResponse(message="Space view updated successfully", id=entity_id)


@router.delete("/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_space_view(entity_id: int):
    response = await db_client.space_view.delete(entity_id=entity_id)
    if not response.get("success"):
        error = response.get("error", "Failed to delete space view")
        code = status.HTTP_404_NOT_FOUND if "not found" in error.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=error)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
