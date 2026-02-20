from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, Sequence, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .space import Space
    from .user import User


class SpaceView(Base):
    __tablename__ = "object_space_views"

    id: Mapped[int] = mapped_column(
        Integer, Sequence("object_space_views_id_seq"), primary_key=True
    )
    space_id: Mapped[int] = mapped_column(
        ForeignKey("object_spaces.id", ondelete="CASCADE")
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE")
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    space: Mapped["Space"] = relationship(back_populates="views")
    user: Mapped["User"] = relationship(back_populates="space_views")
