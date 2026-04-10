from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_current_user
from api.schemas.telegram_chats import TelegramChatResponse
from shared.clients.database_client import db_client
from shared.constants import Roles
from shared.schemas.telegram_chat import TelegramChatSchema

router = APIRouter(prefix="/telegram-chats", tags=["Telegram Chats"])


def _require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    role = current_user.get("role")
    if role not in (Roles.ADMIN, Roles.SUPER_ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для просмотра Telegram-чатов.",
        )
    return current_user


@router.get("/", response_model=list[TelegramChatResponse])
async def get_known_telegram_chats(_: dict = Depends(_require_admin)):
    response = await db_client.telegram_chat.get_known_chats(model_class=TelegramChatSchema)
    if not response.get("success"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=response.get("error", "Failed to fetch Telegram chats"),
        )
    return response.get("data", []) or []
