from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class PollAnswerResponse(BaseModel):
    """Response schema for PollAnswer entity."""
    id: Optional[int] = None
    user_id: int
    ddid: str
    answer: str
    meta: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CreatePollRequest(BaseModel):
    """Request body for creating a poll answer."""
    model_config = ConfigDict(extra="forbid")

    user_id: int
    ddid: str
    answer: str
    meta: Optional[str] = None


class UpdatePollBody(BaseModel):
    """Request body for partial poll answer update."""
    model_config = ConfigDict(extra="forbid")

    user_id: Optional[int] = None
    ddid: Optional[str] = None
    answer: Optional[str] = None
    meta: Optional[str] = None
