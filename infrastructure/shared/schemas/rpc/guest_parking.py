"""RPC-схемы для guest_parking service."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

from shared.utils.time_utils import SYSTEM_TIMEZONE


def _ensure_aware(dt: datetime) -> datetime:
    """Naive → Europe/Minsk для хранения в TIMESTAMPTZ."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=SYSTEM_TIMEZONE)
    return dt


class GuestParkingCreateRpc(BaseModel):
    """Валидация model_data для guest_parking.create."""
    model_config = ConfigDict(extra="forbid")

    user_id: int
    object_id: Optional[int] = None
    arrival_date: datetime
    arrival_start_at: datetime
    arrival_end_at: datetime
    license_plate: str = ""
    car_make_color: str = ""
    tenant_phone: Optional[str] = None
    status: str = "NEW"

    @field_validator("arrival_date", "arrival_start_at", "arrival_end_at")
    @classmethod
    def arrival_aware(cls, v: datetime) -> datetime:
        return _ensure_aware(v)


class GuestParkingUpdateRpc(BaseModel):
    """Валидация update_data для guest_parking.update."""
    model_config = ConfigDict(extra="forbid")

    msid: Optional[int] = None
    user_id: Optional[int] = None
    object_id: Optional[int] = None
    arrival_date: Optional[datetime] = None
    arrival_start_at: Optional[datetime] = None
    arrival_end_at: Optional[datetime] = None
    license_plate: Optional[str] = None
    car_make_color: Optional[str] = None
    tenant_phone: Optional[str] = None
    status: Optional[str] = None
    reviewed_by_user_id: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None

    @field_validator("arrival_date", "arrival_start_at", "arrival_end_at", "reviewed_at")
    @classmethod
    def arrival_aware(cls, v: Optional[datetime]) -> Optional[datetime]:
        return _ensure_aware(v) if v is not None else None
