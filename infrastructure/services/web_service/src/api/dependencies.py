"""FastAPI dependencies for auth and request context."""
from fastapi import HTTPException, Request, status

from api.routers.auth import _decode_access_token


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
