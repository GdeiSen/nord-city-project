import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Optional

import jwt
from fastapi import APIRouter, HTTPException, Request, status

from shared.clients.database_client import db_client
from shared.clients.bot_client import bot_client
from shared.constants import Roles
from api.schemas.auth import (
    RequestOtpBody,
    RequestOtpResponse,
    VerifyOtpBody,
    VerifyOtpResponse,
    TokenValidationResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Auth"])

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))


def _create_access_token(user_id: int, role: int) -> str:
    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def _decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


async def _resolve_user_id(body: RequestOtpBody) -> int:
    """Resolve user_id from body. If username provided, lookup in database."""
    if body.user_id is not None:
        return body.user_id
    # Lookup by username (case-insensitive, strip leading @)
    username = (body.username or "").strip().lstrip("@")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Укажите Telegram ID или имя пользователя (@username).",
        )
    result = await db_client.user.get_by_username(username=username)
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при поиске пользователя.",
        )
    user_data = result.get("data")
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Пользователь @{username} не найден.",
        )
    user_id = user_data.get("id") if isinstance(user_data, dict) else getattr(user_data, "id", None)
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден.")
    return int(user_id)


@router.post("/request-otp", response_model=RequestOtpResponse)
async def request_otp(body: RequestOtpBody):
    try:
        user_id = await _resolve_user_id(body)

        result = await bot_client.telegram_auth.send_otp_code(user_id=user_id)

        if not result.get("success"):
            error = result.get("error", "unknown_error")
            error_messages = {
                "user_not_found": "Пользователь не найден.",
                "insufficient_permissions": "Нет прав для доступа к панели управления.",
            }
            message = error_messages.get(error, "Не удалось отправить код.")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=message)

        return RequestOtpResponse(
            success=True,
            message="Код подтверждения отправлен в Telegram.",
            user_id=user_id,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error requesting OTP: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при отправке кода."
        )


@router.post("/verify-otp", response_model=VerifyOtpResponse)
async def verify_otp(body: VerifyOtpBody):
    try:
        result = await db_client.otp.verify_code(user_id=body.user_id, code=body.code)

        if not result.get("success") or result.get("data") is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный или истекший код."
            )

        user_result = await db_client.user.get_by_id(entity_id=body.user_id)
        if not user_result.get("success") or user_result.get("data") is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден."
            )

        user_data = user_result["data"]
        user_role = user_data.get("role")

        if user_role not in (Roles.ADMIN, Roles.SUPER_ADMIN):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нет прав для доступа к панели управления."
            )

        access_token = _create_access_token(body.user_id, user_role)

        return VerifyOtpResponse(
            success=True,
            message="Авторизация успешна.",
            access_token=access_token,
            user={
                "id": user_data.get("id"),
                "username": user_data.get("username"),
                "first_name": user_data.get("first_name"),
                "last_name": user_data.get("last_name"),
                "role": user_role,
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying OTP: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при проверке кода."
        )


@router.get("/validate", response_model=TokenValidationResponse)
async def validate_token(request: Request):
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return TokenValidationResponse(valid=False)

    token = auth_header.split(" ", 1)[1]
    payload = _decode_access_token(token)

    if payload is None:
        return TokenValidationResponse(valid=False)

    return TokenValidationResponse(
        valid=True,
        user_id=int(payload["sub"]),
        role=payload.get("role"),
    )
