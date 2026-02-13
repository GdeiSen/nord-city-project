from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import BigInteger, String, DateTime, func, ForeignKey, Text, Integer, Sequence
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base

if TYPE_CHECKING:
    from .user import User

class PollAnswer(Base):
    __tablename__ = 'poll_answers'
    id: Mapped[int] = mapped_column(Integer, Sequence('poll_answers_id_seq'), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.id'))
    ddid: Mapped[str] = mapped_column(String(14))
    answer: Mapped[str] = mapped_column(String(255))
    meta: Mapped[Optional[str]] = mapped_column(Text)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship(back_populates="poll_answers")