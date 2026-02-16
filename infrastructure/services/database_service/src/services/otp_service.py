import logging
from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import select, and_
from database.database_manager import DatabaseManager
from shared.models.otp_code import OtpCode
from shared.utils.converter import Converter
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

    # Override BaseService.create to normalise expires_at before insert
    @db_session_manager
    async def create(self, *, session, model_instance: OtpCode | Dict[str, Any]) -> Optional[OtpCode]:
        """
        Create a new OTP code.

        Normalises ``expires_at`` to a proper ``datetime`` instance to avoid
        asyncpg errors when the value is provided as an ISO string.
        """
        # When called via RPC, model_instance will typically be a dict that
        # came from JSON and Converter.to_dict on the client side.
        if isinstance(model_instance, dict):
            expires = model_instance.get("expires_at")
            if isinstance(expires, str):
                try:
                    # fromisoformat can handle 'YYYY-MM-DDTHH:MM:SS[.ffffff]'
                    model_instance["expires_at"] = datetime.fromisoformat(expires)
                except Exception:
                    logger.warning("Failed to parse expires_at from string for OtpCode")
            model_instance = Converter.from_dict(self.model_class, model_instance)
        elif isinstance(model_instance, OtpCode) and isinstance(model_instance.expires_at, str):
            try:
                model_instance.expires_at = datetime.fromisoformat(model_instance.expires_at)
            except Exception:
                logger.warning("Failed to parse expires_at on OtpCode instance")

        created_instance = await self.repository.create(session=session, obj_in=model_instance)
        if created_instance is None:
            raise Exception("Failed to create new OtpCode in the database.")
        logger.info("OtpCode created for user_id=%s", created_instance.user_id)
        return created_instance

    @db_session_manager
    async def verify_code(self, *, session, user_id: int, code: str) -> Optional[OtpCode]:
        """
        Verify an OTP code for a given user.
        Returns the OTP record if valid and not expired, None otherwise.
        Marks the code as used upon successful verification.
        """
        # Use naive UTC datetime to match TIMESTAMP WITHOUT TIME ZONE
        now = datetime.utcnow()
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
        # Use naive UTC datetime to match TIMESTAMP WITHOUT TIME ZONE
        now = datetime.utcnow()
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
