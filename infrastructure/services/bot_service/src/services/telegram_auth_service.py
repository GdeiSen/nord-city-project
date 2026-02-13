# ./services/telegram_auth_service.py
"""
Service for handling Telegram-based authentication.

Responsible for:
- Generating and sending OTP codes to users via Telegram
- Storing OTP codes in the database for verification
- Validating that users have the required role (ADMIN/SUPER_ADMIN)
"""

import logging
import secrets
import string
from datetime import datetime, timezone, timedelta
from typing import TYPE_CHECKING, Optional, Dict, Any

from telegram.constants import ParseMode

from shared.constants import Roles
from shared.models.otp_code import OtpCode
from .base_service import BaseService

if TYPE_CHECKING:
    from bot import Bot

logger = logging.getLogger(__name__)

# OTP code settings
OTP_CODE_LENGTH = 6
OTP_CODE_TTL_MINUTES = 5


class TelegramAuthService(BaseService):
    """
    Service for Telegram-based OTP authentication.

    Handles the full OTP lifecycle:
    1. Receives a request to send an OTP code to a user
    2. Validates user exists and has ADMIN or SUPER_ADMIN role
    3. Generates a 6-digit OTP code
    4. Stores the code in the database with an expiration time
    5. Sends the code to the user via Telegram bot
    """

    def __init__(self, bot: "Bot"):
        super().__init__(bot)

    async def initialize(self) -> None:
        """Initialize the authentication service."""
        logger.info("TelegramAuthService initialized")

    async def send_otp_code(self, user_id: int) -> Dict[str, Any]:
        """
        Generate and send an OTP code to the specified user via Telegram.

        Args:
            user_id: The Telegram user ID to send the code to.

        Returns:
            Dict with keys: success (bool), error (str | None)
        """
        try:
            # 1. Check user exists and has required role
            user = await self.bot.services.user.get_user_by_id(user_id)
            if not user:
                logger.warning(f"OTP request for non-existent user: {user_id}")
                return {"success": False, "error": "user_not_found"}

            user_role = getattr(user, 'role', None)
            if user_role not in (Roles.ADMIN, Roles.SUPER_ADMIN):
                logger.warning(f"OTP request for user without admin role: {user_id} (role={user_role})")
                return {"success": False, "error": "insufficient_permissions"}

            # 2. Invalidate any existing active codes for this user
            await self.bot.managers.database.otp.invalidate_user_codes(user_id=user_id)

            # 3. Generate a 6-digit OTP code
            code = self._generate_otp_code()
            # Use naive UTC datetime because the column is TIMESTAMP WITHOUT TIME ZONE
            expires_at = datetime.utcnow() + timedelta(minutes=OTP_CODE_TTL_MINUTES)

            # 4. Store the code in database
            otp_data = {
                "user_id": user_id,
                "code": code,
                "is_used": False,
                "expires_at": expires_at,
            }
            result = await self.bot.managers.database.otp.create(model_data=otp_data)
            if not result.get("success"):
                logger.error(f"Failed to store OTP code for user {user_id}: {result.get('error')}")
                return {"success": False, "error": "failed_to_create_code"}

            # 5. Send the code to the user via Telegram
            message_text = (
                f"🔐 <b>Код подтверждения</b>\n\n"
                f"Ваш код для входа в панель управления:\n\n"
                f"<code>{code}</code>\n\n"
                f"Код действителен {OTP_CODE_TTL_MINUTES} минут.\n"
                f"Если вы не запрашивали код, проигнорируйте это сообщение."
            )

            await self.bot.application.bot.send_message(
                chat_id=user_id,
                text=message_text,
                parse_mode=ParseMode.HTML
            )

            logger.info(f"OTP code sent to user {user_id}")
            return {"success": True, "error": None}

        except Exception as e:
            logger.error(f"Error sending OTP code to user {user_id}: {e}", exc_info=True)
            return {"success": False, "error": f"internal_error: {str(e)}"}

    def _generate_otp_code(self) -> str:
        """Generate a cryptographically secure 6-digit OTP code."""
        return ''.join(secrets.choice(string.digits) for _ in range(OTP_CODE_LENGTH))
