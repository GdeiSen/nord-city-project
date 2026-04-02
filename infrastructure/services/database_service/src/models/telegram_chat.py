from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .object import Object


class TelegramChat(Base):
    __tablename__ = "telegram_chats"

    chat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    title: Mapped[str] = mapped_column(String(255), default="")
    chat_type: Mapped[str] = mapped_column(String(32), default="group")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    bot_status: Mapped[Optional[str]] = mapped_column(String(64))
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=func.now())
    meta: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    objects: Mapped[list["Object"]] = relationship(back_populates="admin_chat")
