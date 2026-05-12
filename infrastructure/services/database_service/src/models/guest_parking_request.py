from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, Sequence, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .object import Object
    from .user import User


class GuestParkingRequest(Base):
    __tablename__ = "guest_parking_requests"

    id: Mapped[int] = mapped_column(
        Integer, Sequence("guest_parking_requests_id_seq"), primary_key=True
    )
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    object_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("objects.id"))
    msid: Mapped[Optional[int]] = mapped_column(BigInteger)  # message_id в чате администраторов
    arrival_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    arrival_start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    arrival_end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    license_plate: Mapped[str] = mapped_column(String(20))
    car_make_color: Mapped[str] = mapped_column(String(200))
    tenant_phone: Mapped[Optional[str]] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(20), default="NEW")
    reviewed_by_user_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("users.id"))
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    rejection_reason: Mapped[Optional[str]] = mapped_column(String(500))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    user: Mapped["User"] = relationship(back_populates="guest_parking_requests")
    object: Mapped[Optional["Object"]] = relationship()
