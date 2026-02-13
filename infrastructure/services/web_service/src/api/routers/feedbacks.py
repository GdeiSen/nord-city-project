import logging
from typing import List

from fastapi import APIRouter, HTTPException, Response, status

from shared.clients.database_client import db_client
from api.schemas.common import MessageResponse
from api.schemas.feedbacks import FeedbackResponse, CreateFeedbackRequest, UpdateFeedbackBody

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/feedbacks", tags=["Feedbacks"])


@router.post("/", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def create_feedback(body: CreateFeedbackRequest):
    response = await db_client.feedback.create(model_data=body.model_dump())
    if not response.get("success"):
        error = response.get("error", "Failed to create feedback")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return response["data"]


@router.get("/", response_model=List[FeedbackResponse])
async def get_all_feedbacks():
    response = await db_client.feedback.get_all()
    if not response.get("success"):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=response.get("error", "Failed to fetch feedbacks"))
    return response.get("data", [])


@router.get("/{entity_id}", response_model=FeedbackResponse)
async def get_feedback_by_id(entity_id: int):
    response = await db_client.feedback.get_by_id(entity_id=entity_id)
    if not response.get("success"):
        error = response.get("error", "Feedback not found")
        code = status.HTTP_404_NOT_FOUND if "not found" in error.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=error)
    if response.get("data") is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feedback not found")
    return response["data"]


@router.put("/{entity_id}", response_model=MessageResponse)
async def update_feedback(entity_id: int, body: UpdateFeedbackBody):
    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    response = await db_client.feedback.update(entity_id=entity_id, update_data=update_data)
    if not response.get("success"):
        error = response.get("error", "Failed to update feedback")
        code = status.HTTP_404_NOT_FOUND if "not found" in error.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=error)
    return MessageResponse(message="Feedback updated successfully", id=entity_id)


@router.delete("/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_feedback(entity_id: int):
    response = await db_client.feedback.delete(entity_id=entity_id)
    if not response.get("success"):
        error = response.get("error", "Failed to delete feedback")
        code = status.HTTP_404_NOT_FOUND if "not found" in error.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=error)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
