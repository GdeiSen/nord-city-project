import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Optional

import jwt
from fastapi import APIRouter, HTTPException, Request, status

from shared.clients.database_client import db_client
from shared.clients.bot_client import bot_client
from shared.constants import AuditRetentionClass, Roles
from shared.schemas.user import UserSchema
from shared.utils.audit_context import build_request_audit_context
from shared.utils.audit_events import append_business_audit_event
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


def _build_auth_audit_context(request: Request, *, user_id: int) -> dict:
    return build_request_audit_context(
        request,
        {"user_id": int(user_id)},
        source_service="web_service",
        reason="auth_flow_event",
        meta={"auth_flow": "otp", "auth_actor_origin": "web_auth"},
    )


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
    result = await db_client.user.get_by_username(username=username, model_class=UserSchema)
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при поиске пользователя.",
        )
    user_schema = result.get("data")
    if not user_schema:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Пользователь @{username} не найден.",
        )
    return int(user_schema.id)


@router.post("/request-otp", response_model=RequestOtpResponse)
async def request_otp(body: RequestOtpBody, request: Request):
    try:
        try:
            user_id = await _resolve_user_id(body)
        except HTTPException as exc:
            fallback_audit_context = build_request_audit_context(
                request,
                None,
                source_service="web_service",
                reason="otp_request_failed",
                meta={
                    "auth_flow": "otp",
                    "auth_stage": "request",
                    "requested_user_id": body.user_id,
                    "requested_username": (body.username or "").strip(),
                },
            )
            await append_business_audit_event(
                entity_type="User",
                entity_id=int(body.user_id or 0),
                event_type="OTP_REQUEST_FAILED",
                event_name="user.otp_request_failed",
                action="send",
                source_service="web_service",
                audit_context=fallback_audit_context,
                retention_class=AuditRetentionClass.CRITICAL,
                reason="otp_request_failed",
                meta={
                    "auth_flow": "otp",
                    "auth_stage": "request",
                    "requested_user_id": body.user_id,
                    "requested_username": (body.username or "").strip(),
                    "error": str(exc.detail),
                },
                audit_type="smart",
            )
            raise
        audit_context = _build_auth_audit_context(request, user_id=user_id)

        audit_response = await append_business_audit_event(
            entity_type="User",
            entity_id=int(user_id),
            event_type="OTP_REQUESTED",
            event_name="user.otp_requested",
            action="send",
            source_service="web_service",
            audit_context=audit_context,
            retention_class=AuditRetentionClass.CRITICAL,
            reason="otp_requested",
            meta={
                "auth_flow": "otp",
                "auth_stage": "request",
            },
            audit_type="smart",
        )
        if not audit_response.get("success"):
            logger.warning("OTP request audit append failed: %s", audit_response.get("error"))

        result = await bot_client.telegram_auth.send_otp_code(
            user_id=user_id,
            _audit_context=audit_context,
        )

        if not result.get("success"):
            error = result.get("error", "unknown_error")
            await append_business_audit_event(
                entity_type="User",
                entity_id=int(user_id),
                event_type="OTP_REQUEST_FAILED",
                event_name="user.otp_request_failed",
                action="send",
                source_service="web_service",
                audit_context=audit_context,
                retention_class=AuditRetentionClass.CRITICAL,
                reason="otp_request_failed",
                meta={
                    "auth_flow": "otp",
                    "auth_stage": "request",
                    "error": error,
                },
                audit_type="smart",
            )
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
async def verify_otp(body: VerifyOtpBody, request: Request):
    try:
        audit_context = _build_auth_audit_context(request, user_id=body.user_id)
        result = await db_client.otp.verify_code(user_id=body.user_id, code=body.code)

        if not result.get("success") or result.get("data") is None:
            await append_business_audit_event(
                entity_type="User",
                entity_id=int(body.user_id),
                event_type="OTP_VERIFICATION_FAILED",
                event_name="user.otp_verification_failed",
                action="verify",
                source_service="web_service",
                audit_context=audit_context,
                retention_class=AuditRetentionClass.CRITICAL,
                reason="otp_verification_failed",
                meta={
                    "auth_flow": "otp",
                    "auth_stage": "verify",
                    "error": "invalid_or_expired_code",
                },
                audit_type="smart",
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный или истекший код."
            )

        user_result = await db_client.user.get_by_id(entity_id=body.user_id, model_class=UserSchema)
        if not user_result.get("success") or user_result.get("data") is None:
            await append_business_audit_event(
                entity_type="User",
                entity_id=int(body.user_id),
                event_type="OTP_VERIFICATION_FAILED",
                event_name="user.otp_verification_failed",
                action="verify",
                source_service="web_service",
                audit_context=audit_context,
                retention_class=AuditRetentionClass.CRITICAL,
                reason="otp_verification_failed",
                meta={
                    "auth_flow": "otp",
                    "auth_stage": "verify",
                    "error": "user_not_found_after_code_verification",
                },
                audit_type="smart",
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден."
            )

        user_schema = user_result["data"]

        if user_schema.role not in (Roles.ADMIN, Roles.SUPER_ADMIN):
            await append_business_audit_event(
                entity_type="User",
                entity_id=int(body.user_id),
                event_type="AUTHORIZATION_DENIED",
                event_name="user.authorization_denied_after_otp",
                action="verify",
                source_service="web_service",
                audit_context=audit_context,
                retention_class=AuditRetentionClass.CRITICAL,
                reason="authorization_denied_after_otp",
                meta={
                    "auth_flow": "otp",
                    "auth_stage": "verify",
                    "resolved_role": user_schema.role,
                },
                audit_type="smart",
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нет прав для доступа к панели управления."
            )

        access_token = _create_access_token(body.user_id, user_schema.role)

        audit_response = await append_business_audit_event(
            entity_type="User",
            entity_id=int(body.user_id),
            event_type="OTP_VERIFIED",
            event_name="user.otp_verified",
            action="verify",
            source_service="web_service",
            audit_context=audit_context,
            retention_class=AuditRetentionClass.CRITICAL,
            reason="otp_verified",
            meta={
                "auth_flow": "otp",
                "auth_stage": "verify",
                "resolved_role": user_schema.role,
            },
            audit_type="smart",
        )
        if not audit_response.get("success"):
            logger.warning("OTP verification audit append failed: %s", audit_response.get("error"))

        return VerifyOtpResponse(
            success=True,
            message="Авторизация успешна.",
            access_token=access_token,
            user={
                "id": user_schema.id,
                "username": user_schema.username,
                "first_name": user_schema.first_name,
                "last_name": user_schema.last_name,
                "role": user_schema.role,
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
        return TokenValidationResponse(valid=False, reason="missing_token")

    token = auth_header.split(" ", 1)[1]
    payload = _decode_access_token(token)

    if payload is None:
        return TokenValidationResponse(valid=False, reason="invalid_token")

    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        return TokenValidationResponse(valid=False, reason="invalid_payload")

    user_result = await db_client.user.get_by_id(entity_id=user_id, model_class=UserSchema)
    if not user_result.get("success") or user_result.get("data") is None:
        return TokenValidationResponse(valid=False, reason="access_restricted")

    user_schema = user_result["data"]
    if user_schema.role not in (Roles.ADMIN, Roles.SUPER_ADMIN):
        return TokenValidationResponse(valid=False, reason="access_restricted")

    return TokenValidationResponse(
        valid=True,
        user_id=user_id,
        role=user_schema.role,
        reason=None,
    )
