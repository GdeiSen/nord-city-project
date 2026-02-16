from datetime import datetime
from sqlalchemy import BigInteger, String, DateTime, func, ForeignKey, Integer, Sequence
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .user import User

class UserAuth(Base):
    __tablename__ = 'user_auth'
    id: Mapped[int] = mapped_column(Integer, Sequence('user_auth_id_seq'), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('users.id'))
    password_hash: Mapped[str] = mapped_column(String(256))
    
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship(back_populates="auth")