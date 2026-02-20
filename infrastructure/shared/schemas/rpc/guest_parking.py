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
    arrival_date: datetime
    license_plate: str = ""
    car_make_color: str = ""
    driver_phone: str = ""
    tenant_phone: Optional[str] = None

    @field_validator("arrival_date")
    @classmethod
    def arrival_aware(cls, v: datetime) -> datetime:
        return _ensure_aware(v)


class GuestParkingUpdateRpc(BaseModel):
    """Валидация update_data для guest_parking.update. msid — ID сообщения (сохраняет бот)."""
    model_config = ConfigDict(extra="forbid")

    msid: Optional[int] = None
    user_id: Optional[int] = None
    arrival_date: Optional[datetime] = None
    license_plate: Optional[str] = None
    car_make_color: Optional[str] = None
    driver_phone: Optional[str] = None
    tenant_phone: Optional[str] = None

    @field_validator("arrival_date")
    @classmethod
    def arrival_aware(cls, v: Optional[datetime]) -> Optional[datetime]:
        return _ensure_aware(v) if v is not None else None
