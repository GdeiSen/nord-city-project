from datetime import datetime
from typing import TYPE_CHECKING, Any, List, Optional

from sqlalchemy import DateTime, Integer, JSON, Sequence, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .space import Space
    from .user import User


class Object(Base):
    __tablename__ = "objects"
    id: Mapped[int] = mapped_column(Integer, Sequence("objects_id_seq"), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    address: Mapped[str] = mapped_column(String(500))
    description: Mapped[Optional[str]] = mapped_column(Text)
    photos: Mapped[List[Any]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(100), default="ACTIVE")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    spaces: Mapped[List["Space"]] = relationship(back_populates="object", cascade="all, delete-orphan")
    users: Mapped[List["User"]] = relationship(back_populates="object")
