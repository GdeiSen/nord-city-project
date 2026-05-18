from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Index, Integer, JSON, Sequence, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class BotInteractionSession(Base):
    __tablename__ = "bot_interaction_sessions"

    id: Mapped[int] = mapped_column(
        Integer,
        Sequence("bot_interaction_sessions_id_seq"),
        primary_key=True,
        server_default=text("nextval('bot_interaction_sessions_id_seq'::regclass)"),
    )
    session_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    owner_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    prompt_message_id: Mapped[Optional[int]] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="ACTIVE")
    meta: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        Index("ix_bot_interaction_sessions_entity", "entity_type", "entity_id"),
        Index("ix_bot_interaction_sessions_chat", "session_type", "chat_id", "status"),
        Index("ix_bot_interaction_sessions_owner", "session_type", "owner_user_id", "status"),
        Index(
            "uq_bot_interaction_sessions_active_chat",
            "session_type",
            "chat_id",
            unique=True,
            postgresql_where=text("status = 'ACTIVE'"),
        ),
        Index(
            "uq_bot_interaction_sessions_active_owner",
            "session_type",
            "owner_user_id",
            unique=True,
            postgresql_where=text("status = 'ACTIVE'"),
        ),
    )
