from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class GuestParkingSchema(BaseModel):
    """Pydantic schema for GuestParkingRequest entity. Mirrors ORM."""

    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    user_id: int = 0
    msid: Optional[int] = None
    arrival_date: Optional[datetime] = None
    license_plate: str = ""
    car_make_color: str = ""
    driver_phone: str = ""
    tenant_phone: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
