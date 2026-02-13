from datetime import datetime
from sqlalchemy import BigInteger, String, DateTime, Boolean, Integer, Sequence, func
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class OtpCode(Base):
    """
    Model for storing OTP verification codes sent via Telegram bot.
    
    Each record represents a single OTP code issued for a user (identified by
    their Telegram user_id). Codes expire after a configurable TTL and are
    marked as used once successfully verified.
    """
    __tablename__ = 'otp_codes'

    id: Mapped[int] = mapped_column(Integer, Sequence('otp_codes_id_seq'), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(6), nullable=False)
    is_used: Mapped[bool] = mapped_column(Boolean, default=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
