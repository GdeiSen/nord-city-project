"""FastAPI dependencies for auth and request context."""
from typing import Optional

from fastapi import HTTPException, Request, status

from api.routers.auth import _decode_access_token


def get_audit_context(request: Request, current_user: Optional[dict] = None) -> dict:
    """
    Build audit context for db_client calls: assignee_id, source (caller service).
    Pass to create/update/delete as _audit_context=... for audit logging.
    """
    ctx = {"source": "web_service"}
    if current_user and "user_id" in current_user:
        ctx["assignee_id"] = current_user["user_id"]
    return ctx


def get_optional_current_user(request: Request) -> Optional[dict]:
    """Extract current user from token if present; returns None if missing/invalid."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ", 1)[1]
    payload = _decode_access_token(token)
    if payload is None:
        return None
    user_id = payload.get("sub")
    role = payload.get("role")
    if not user_id:
        return None
    return {"user_id": int(user_id), "role": role}


def get_current_user(request: Request) -> dict:
    """
    Extract current user from Authorization Bearer token.
    Raises 401 if token is missing or invalid.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется авторизация",
        )
    token = auth_header.split(" ", 1)[1]
    payload = _decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный или истекший токен",
        )
    user_id = payload.get("sub")
    role = payload.get("role")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный формат токена",
        )
    return {"user_id": int(user_id), "role": role}
