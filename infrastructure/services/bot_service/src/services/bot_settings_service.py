from typing import TYPE_CHECKING, Any, Dict

from bot_features import (
    BOT_FEATURES_BY_DIALOG,
    BOT_FEATURES_BY_KEY,
    DEFAULT_MENU_LAYOUT,
    LIMITED_MENU_LAYOUT,
)
from settings.bot_settings import get_bot_settings, save_bot_settings
from shared.constants import Dialogs, Roles, Variables

from .base_service import BaseService

if TYPE_CHECKING:
    from telegram.ext import ContextTypes
    from bot import Bot


class BotSettingsService(BaseService):
    def __init__(self, bot: "Bot"):
        super().__init__(bot)

    async def initialize(self) -> None:
        return None

    async def get_settings(self) -> Dict[str, Any]:
        return {"success": True, "data": get_bot_settings()}

    async def update_settings(self, *, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            updated_data = save_bot_settings(data)
            return {"success": True, "data": updated_data}
        except (TypeError, ValueError) as exc:
            return {"success": False, "error": f"validation_error: {exc}"}
        except Exception as exc:
            return {"success": False, "error": f"update_failed: {exc}"}

    def get_settings_snapshot(self) -> Dict[str, Any]:
        return get_bot_settings()

    def is_feature_enabled(self, feature_key: str) -> bool:
        feature_config = self.get_settings_snapshot().get("features", {}).get(feature_key, {})
        return bool(feature_config.get("enabled", False))

    def get_feature_by_key(self, feature_key: str):
        return BOT_FEATURES_BY_KEY.get(feature_key)

    def get_feature_key_for_route(
        self,
        route_id: int | str,
        context: "ContextTypes.DEFAULT_TYPE | None" = None,
    ) -> str | None:
        if route_id == Dialogs.DYN_DIALOG_ITEM and context is not None:
            active_dialog = self.bot.managers.storage.get(context, Variables.ACTIVE_DYN_DIALOG)
            dialog_id = getattr(active_dialog, "id", None)
            feature = BOT_FEATURES_BY_DIALOG.get(dialog_id)
            return feature.key if feature else None

        feature = BOT_FEATURES_BY_DIALOG.get(route_id) if isinstance(route_id, int) else None
        return feature.key if feature else None

    def get_enabled_menu_layout(self, role: int | None) -> list[list[tuple[str, int]]]:
        layout = LIMITED_MENU_LAYOUT if role in (Roles.MA, Roles.GUEST) else DEFAULT_MENU_LAYOUT
        rows: list[list[tuple[str, int]]] = []
        for row in layout:
            enabled_items: list[tuple[str, int]] = []
            for feature_key in row:
                feature = BOT_FEATURES_BY_KEY[feature_key]
                if not self.is_feature_enabled(feature_key):
                    continue
                enabled_items.append((feature.label_key, feature.dialog_id))
            if enabled_items:
                rows.append(enabled_items)
        return rows

    def get_enabled_menu_feature_keys(self, role: int | None) -> list[str]:
        layout = LIMITED_MENU_LAYOUT if role in (Roles.MA, Roles.GUEST) else DEFAULT_MENU_LAYOUT
        return [
            feature_key
            for row in layout
            for feature_key in row
            if self.is_feature_enabled(feature_key)
        ]
