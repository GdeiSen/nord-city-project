import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, and_
from database.database_manager import DatabaseManager
from models.otp_code import OtpCode
from .base_service import BaseService, db_session_manager

logger = logging.getLogger(__name__)


class OtpService(BaseService):
    """
    Service for OTP code management.
    Extends BaseService with custom methods for OTP verification workflow.
    """
    model_class = OtpCode

    def __init__(self, db_manager: DatabaseManager):
        super().__init__(db_manager)

    @db_session_manager
    async def verify_code(self, *, session, user_id: int, code: str) -> Optional[OtpCode]:
        """
        Verify an OTP code for a given user.
        Returns the OTP record if valid and not expired, None otherwise.
        Marks the code as used upon successful verification.
        """
        now = datetime.now(timezone.utc)
        stmt = select(OtpCode).where(
            and_(
                OtpCode.user_id == user_id,
                OtpCode.code == code,
                OtpCode.is_used == False,
                OtpCode.expires_at > now,
            )
        ).order_by(OtpCode.created_at.desc()).limit(1)

        result = await session.execute(stmt)
        otp = result.scalar_one_or_none()

        if otp:
            otp.is_used = True
            await session.commit()
            await session.refresh(otp)
            logger.info(f"OTP code verified for user_id={user_id}")

        return otp

    @db_session_manager
    async def invalidate_user_codes(self, *, session, user_id: int) -> int:
        """
        Mark all active (unused, non-expired) OTP codes for a user as used.
        Called before issuing a new code to prevent multiple valid codes.
        Returns the count of invalidated codes.
        """
        now = datetime.now(timezone.utc)
        stmt = select(OtpCode).where(
            and_(
                OtpCode.user_id == user_id,
                OtpCode.is_used == False,
                OtpCode.expires_at > now,
            )
        )
        result = await session.execute(stmt)
        codes = result.scalars().all()

        count = 0
        for code in codes:
            code.is_used = True
            count += 1

        if count > 0:
            await session.commit()
            logger.info(f"Invalidated {count} OTP codes for user_id={user_id}")

        return count
