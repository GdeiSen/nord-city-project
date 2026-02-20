from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

from api.schemas.enrichment import UserSummary


class FeedbackResponse(BaseModel):
    """Response schema for Feedback entity."""
    id: Optional[int] = None
    user_id: int
    user: Optional[UserSummary] = None  # Enriched from user_id
    ddid: str
    answer: str
    text: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CreateFeedbackRequest(BaseModel):
    """Request body for creating feedback. Matches Omit<Feedback, 'id'|'created_at'|'updated_at'>."""
    model_config = ConfigDict(extra="forbid")

    user_id: int
    ddid: str
    answer: str
    text: Optional[str] = None


class UpdateFeedbackBody(BaseModel):
    """Request body for partial feedback update."""
    model_config = ConfigDict(extra="forbid")

    user_id: Optional[int] = None
    ddid: Optional[str] = None
    answer: Optional[str] = None
    text: Optional[str] = None
