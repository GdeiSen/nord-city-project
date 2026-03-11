from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_current_user
from api.schemas.localization import LocalizationDocument
from shared.clients.bot_client import bot_client
from shared.constants import Roles

router = APIRouter(prefix="/localization", tags=["Localization"])


def _require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    role = current_user.get("role")
    if role not in (Roles.ADMIN, Roles.SUPER_ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ только для администраторов.",
        )
    return current_user


@router.get("/", response_model=LocalizationDocument)
async def get_localization(_: dict = Depends(_require_admin)):
    response = await bot_client.localization.get_localization()
    if not response.get("success"):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=response.get("error", "Не удалось получить локализацию из bot_service."),
        )

    payload = response.get("data")
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="bot_service вернул некорректный формат локализации.",
        )
    return LocalizationDocument(root=payload)


@router.put("/", response_model=LocalizationDocument)
async def update_localization(
    body: LocalizationDocument,
    _: dict = Depends(_require_admin),
):
    response = await bot_client.localization.update_localization(data=body.root)
    if not response.get("success"):
        error = str(response.get("error", "Не удалось обновить локализацию."))
        is_validation_error = error.startswith("validation_error:")
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
                if is_validation_error
                else status.HTTP_502_BAD_GATEWAY
            ),
            detail=error,
        )

    payload = response.get("data")
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="bot_service вернул некорректный формат после обновления локализации.",
        )
    return LocalizationDocument(root=payload)
