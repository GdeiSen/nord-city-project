from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

from shared.constants import FeedbackTypes
from api.schemas.enrichment import ServiceTicketSummary, UserSummary


class FeedbackResponse(BaseModel):
    """Response schema for Feedback entity."""
    id: Optional[int] = None
    user_id: int
    user: Optional[UserSummary] = None  # Enriched from user_id
    ddid: str
    feedback_type: str = FeedbackTypes.GENERAL
    answer: str
    text: Optional[str] = None
    service_ticket_id: Optional[int] = None
    service_ticket: Optional[ServiceTicketSummary] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CreateFeedbackRequest(BaseModel):
    """Request body for creating feedback. Matches Omit<Feedback, 'id'|'created_at'|'updated_at'>."""
    model_config = ConfigDict(extra="forbid")

    user_id: int
    ddid: str
    feedback_type: str = FeedbackTypes.GENERAL
    answer: str
    text: Optional[str] = None


class UpdateFeedbackBody(BaseModel):
    """Request body for partial feedback update."""
    model_config = ConfigDict(extra="forbid")

    user_id: Optional[int] = None
    ddid: Optional[str] = None
    feedback_type: Optional[str] = None
    answer: Optional[str] = None
    text: Optional[str] = None
