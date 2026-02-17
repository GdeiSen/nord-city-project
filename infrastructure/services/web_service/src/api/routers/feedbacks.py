import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status

from shared.clients.database_client import db_client
from shared.constants import Roles
from api.dependencies import get_current_user
from api.schemas.common import MessageResponse, PaginatedResponse
from api.helpers.paginated_list import create_paginated_list_handler
from api.helpers.enrichment import enrich_feedbacks_with_users
from api.schemas.feedbacks import FeedbackResponse, CreateFeedbackRequest, UpdateFeedbackBody

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/feedbacks", tags=["Feedbacks"])


@router.post("/", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def create_feedback(
    body: CreateFeedbackRequest,
    current_user: dict = Depends(get_current_user),
):
    if current_user.get("role") != Roles.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только Super Admin может создавать отзывы.",
        )
    response = await db_client.feedback.create(model_data=body.model_dump())
    if not response.get("success"):
        error = response.get("error", "Failed to create feedback")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return response["data"]


get_feedbacks = create_paginated_list_handler(
    db_client.feedback,
    enricher=enrich_feedbacks_with_users,
    entity_label="feedbacks",
)
router.get("/", response_model=PaginatedResponse[FeedbackResponse])(get_feedbacks)


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
async def update_feedback(
    entity_id: int,
    body: UpdateFeedbackBody,
    current_user: dict = Depends(get_current_user),
):
    if current_user.get("role") != Roles.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только Super Admin может редактировать отзывы.",
        )
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
