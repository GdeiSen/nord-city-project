from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

from api.schemas.enrichment import UserSummary


class GuestParkingResponse(BaseModel):
    """Response schema for GuestParkingRequest entity."""
    id: Optional[int] = None
    user_id: int
    user: Optional[UserSummary] = None
    msid: Optional[int] = None
    arrival_date: Optional[datetime] = None
    license_plate: Optional[str] = None
    car_make_color: Optional[str] = None
    driver_phone: Optional[str] = None
    tenant_phone: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CreateGuestParkingBody(BaseModel):
    """Request body for creating guest parking request."""
    model_config = ConfigDict(extra="forbid")

    user_id: int
    arrival_date: datetime
    license_plate: str = ""
    car_make_color: str = ""
    driver_phone: str = ""
    tenant_phone: Optional[str] = None


class UpdateGuestParkingBody(BaseModel):
    """Request body for partial update."""
    model_config = ConfigDict(extra="forbid")

    user_id: Optional[int] = None
    arrival_date: Optional[datetime] = None
    license_plate: Optional[str] = None
    car_make_color: Optional[str] = None
    driver_phone: Optional[str] = None
    tenant_phone: Optional[str] = None
