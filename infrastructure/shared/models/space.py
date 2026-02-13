from datetime import datetime
from typing import List, Optional, Any, TYPE_CHECKING
from sqlalchemy import String, Integer, Boolean, DateTime, func, ForeignKey, Text, JSON, Sequence
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base

if TYPE_CHECKING:
    from .object import Object
    from .space_view import SpaceView

class Space(Base):
    __tablename__ = 'object_spaces'
    
    id: Mapped[int] = mapped_column(Integer, Sequence('object_spaces_id_seq'), primary_key=True)
    object_id: Mapped[int] = mapped_column(ForeignKey('objects.id'))
    floor: Mapped[str] = mapped_column(String(100))
    size: Mapped[int] = mapped_column(Integer)
    description: Mapped[Optional[str]] = mapped_column(Text)
    photos: Mapped[List[Any]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(100), default='FREE')
    
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    
    object: Mapped["Object"] = relationship(back_populates="spaces")
    views: Mapped[List["SpaceView"]] = relationship(back_populates="space", cascade="all, delete-orphan")