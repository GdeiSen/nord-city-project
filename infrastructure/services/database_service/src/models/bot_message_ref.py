from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, JSON, Sequence, String, Index, func, text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class BotMessageRef(Base):
    __tablename__ = "bot_message_refs"

    id: Mapped[int] = mapped_column(
        Integer,
        Sequence("bot_message_refs_id_seq"),
        primary_key=True,
        server_default=text("nextval('bot_message_refs_id_seq'::regclass)"),
    )
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    chat_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("telegram_chats.chat_id"), nullable=False)
    message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False, server_default="PRIMARY")
    meta: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        Index("ix_bot_message_refs_entity", "entity_type", "entity_id"),
        Index("ix_bot_message_refs_chat_message", "chat_id", "message_id", unique=True),
        Index("ix_bot_message_refs_entity_kind", "entity_type", "entity_id", "kind"),
    )
