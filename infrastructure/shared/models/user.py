from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import BigInteger, String, Boolean, Integer, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base
from .user_auth import UserAuth

if TYPE_CHECKING:
    from .user_auth import UserAuth
    from .service_ticket import ServiceTicket
    from .feedback import Feedback
    from .poll_answer import PollAnswer
    from .object import Object
    from .space_view import SpaceView

class User(Base):
    __tablename__ = 'users'
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    username: Mapped[Optional[str]] = mapped_column(String(150))
    role: Mapped[Optional[int]] = mapped_column(Integer)
    first_name: Mapped[Optional[str]] = mapped_column(String(50))
    last_name: Mapped[Optional[str]] = mapped_column(String(50))
    middle_name: Mapped[Optional[str]] = mapped_column(String(50))
    language_code: Mapped[str] = mapped_column(String(2), default="ru")
    data_processing_consent: Mapped[bool] = mapped_column(Boolean, default=False)
    object_id: Mapped[Optional[int]] = mapped_column(ForeignKey('objects.id'))
    legal_entity: Mapped[Optional[str]] = mapped_column(String(500))
    phone_number: Mapped[Optional[str]] = mapped_column(String(40))
    email: Mapped[Optional[str]] = mapped_column(String(100))
    
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    service_tickets: Mapped[List["ServiceTicket"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    feedbacks: Mapped[List["Feedback"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    poll_answers: Mapped[List["PollAnswer"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    object: Mapped["Object"] = relationship(back_populates="users")
    auth: Mapped["UserAuth"] = relationship(back_populates="user", cascade="all, delete-orphan", uselist=False)
    space_views: Mapped[List["SpaceView"]] = relationship(back_populates="user", cascade="all, delete-orphan")