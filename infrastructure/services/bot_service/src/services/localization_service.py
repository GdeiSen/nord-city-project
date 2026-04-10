from typing import TYPE_CHECKING, Any, Dict

from locales.localisation import get_localisation, save_localisation

from .base_service import BaseService

if TYPE_CHECKING:
    from bot import Bot


class LocalizationService(BaseService):
    """RPC service for reading and updating bot localization at runtime."""

    def __init__(self, bot: "Bot"):
        super().__init__(bot)

    async def initialize(self) -> None:
        return None

    async def get_localization(self) -> Dict[str, Any]:
        return {"success": True, "data": get_localisation()}

    async def update_localization(self, *, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            updated_data = save_localisation(data)
            return {"success": True, "data": updated_data}
        except (TypeError, ValueError) as exc:
            return {"success": False, "error": f"validation_error: {exc}"}
        except Exception as exc:
            return {"success": False, "error": f"update_failed: {exc}"}
