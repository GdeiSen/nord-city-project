from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional, List
from datetime import datetime


class ObjectResponse(BaseModel):
    """Response schema for Object (rental object) entity."""
    id: Optional[int] = None
    name: str
    address: str
    description: Optional[str] = None
    photos: List[str] = []
    status: str = "ACTIVE"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_validator("photos", mode="before")
    @classmethod
    def normalise_photos(cls, v):
        """
        Ensure ``photos`` is always a list in API responses.

        Some legacy rows may contain {} or null in the JSON column instead
        of an array; in that case we normalise to an empty list so that
        Pydantic validation and the frontend stay stable.
        """
        if v is None:
            return []
        if isinstance(v, list):
            return v
        # Any non-list value (e.g. {}, string, etc.) -> treat as no photos
        return []


class CreateObjectRequest(BaseModel):
    """Request body for creating a rental object."""
    model_config = ConfigDict(extra="forbid")

    name: str
    address: str
    description: Optional[str] = None
    photos: List[str] = []
    status: str = "ACTIVE"


class UpdateObjectBody(BaseModel):
    """Request body for partial rental object update."""
    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = None
    address: Optional[str] = None
    description: Optional[str] = None
    photos: Optional[List[str]] = None
    status: Optional[str] = None
