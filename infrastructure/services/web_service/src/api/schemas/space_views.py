from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class SpaceViewResponse(BaseModel):
    """Response schema for SpaceView entity."""
    id: Optional[int] = None
    space_id: int
    user_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CreateSpaceViewRequest(BaseModel):
    """Request body for creating a space view."""
    model_config = ConfigDict(extra="forbid")

    space_id: int
    user_id: int


class UpdateSpaceViewBody(BaseModel):
    """Request body for partial space view update."""
    model_config = ConfigDict(extra="forbid")

    space_id: Optional[int] = None
    user_id: Optional[int] = None
