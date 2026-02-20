from datetime import datetime
from typing import TYPE_CHECKING, Any, List, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, Sequence, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .object import Object
    from .space_view import SpaceView


class Space(Base):
    __tablename__ = "object_spaces"

    id: Mapped[int] = mapped_column(Integer, Sequence("object_spaces_id_seq"), primary_key=True)
    object_id: Mapped[int] = mapped_column(ForeignKey("objects.id"))
    floor: Mapped[str] = mapped_column(String(100))
    size: Mapped[float] = mapped_column(Float)
    description: Mapped[Optional[str]] = mapped_column(Text)
    photos: Mapped[List[Any]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(100), default="FREE")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    object: Mapped["Object"] = relationship(back_populates="spaces")
    views: Mapped[List["SpaceView"]] = relationship(
        back_populates="space", cascade="all, delete-orphan"
    )
