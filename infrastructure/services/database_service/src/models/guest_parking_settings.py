from datetime import datetime
from typing import Any, List

from sqlalchemy import DateTime, Integer, JSON, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class GuestParkingSettings(Base):
    __tablename__ = "guest_parking_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    route_images: Mapped[List[Any]] = mapped_column(JSON, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
