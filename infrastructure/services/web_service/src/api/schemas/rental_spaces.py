from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime


class SpaceResponse(BaseModel):
    """Response schema for Space (rental space) entity."""
    id: Optional[int] = None
    object_id: int
    floor: str
    size: float
    description: Optional[str] = None
    photos: List[str] = []
    status: str = "FREE"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CreateSpaceRequest(BaseModel):
    """Request body for creating a rental space."""
    model_config = ConfigDict(extra="forbid")

    object_id: int
    floor: str
    size: float
    description: Optional[str] = None
    photos: List[str] = []
    status: str = "FREE"


class UpdateSpaceBody(BaseModel):
    """Request body for partial rental space update."""
    model_config = ConfigDict(extra="forbid")

    object_id: Optional[int] = None
    floor: Optional[str] = None
    size: Optional[float] = None
    description: Optional[str] = None
    photos: Optional[List[str]] = None
    status: Optional[str] = None
