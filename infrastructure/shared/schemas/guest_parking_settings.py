from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, field_validator


class GuestParkingSettingsSchema(BaseModel):
    """Singleton settings for guest parking flow."""

    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = 1
    route_images: List[str] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_validator("route_images", mode="before")
    @classmethod
    def normalize_route_images(cls, v):
        if v is None:
            return []
        if isinstance(v, list):
            return v
        return []
