from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class GuestParkingSchema(BaseModel):
    """Pydantic schema for GuestParkingRequest entity. Mirrors ORM."""

    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    user_id: int = 0
    object_id: Optional[int] = None
    msid: Optional[int] = None
    arrival_date: Optional[datetime] = None
    arrival_start_at: Optional[datetime] = None
    arrival_end_at: Optional[datetime] = None
    license_plate: str = ""
    car_make_color: str = ""
    tenant_phone: Optional[str] = None
    status: str = "NEW"
    reviewed_by_user_id: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
