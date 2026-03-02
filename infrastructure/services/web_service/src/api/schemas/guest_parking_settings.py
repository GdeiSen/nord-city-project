from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class GuestParkingSettingsResponse(BaseModel):
    id: int = 1
    route_images: List[str] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class UpdateGuestParkingSettingsBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    route_images: List[str] = Field(default_factory=list, max_length=2)
