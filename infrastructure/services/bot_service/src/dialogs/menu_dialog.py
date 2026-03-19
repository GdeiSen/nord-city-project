from typing import TYPE_CHECKING

from shared.constants import Actions, Dialogs, Variables

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes
    from bot import Bot


def _is_profile_complete(user) -> bool:
    return bool(
        user.last_name
        and user.first_name
        and user.middle_name
        and user.legal_entity
    )


def _build_menu_message(bot: "Bot", user) -> str:
    if not _is_profile_complete(user):
        return bot.get_text("new_greeting")
    return bot.get_text("default_greeting")


def _build_menu_keyboard(bot: "Bot", user):
    if not _is_profile_complete(user):
        if bot.services.bot_settings.is_feature_enabled("profile"):
            return bot.create_keyboard([[("login", Dialogs.PROFILE)]])
        return None

    rows = bot.services.bot_settings.get_enabled_menu_layout(user.role)
    if not rows:
        return None
    return bot.create_keyboard(rows)


async def show_main_menu(
    update: "Update",
    context: "ContextTypes.DEFAULT_TYPE",
    bot: "Bot",
) -> int:
    if update.effective_chat.type != "private":
        return

    bot.managers.navigator.set_entry_point(context, Dialogs.MENU)
    user_id = bot.get_user_id(update)

    if user_id is None:
        return Actions.END

    user = await bot.services.user.get_user_by_id(user_id)
    if user is None:
        return Actions.END

    bot.managers.storage.set(
        context,
        Variables.USER_NAME,
        ((user.last_name or "") + " " + (user.first_name or "") + " " + (user.middle_name or "")).strip(),
    )
    bot.managers.storage.set(context, Variables.USER_LEGAL_ENTITY, user.legal_entity or "")

    keyboard = _build_menu_keyboard(bot, user)
    text = _build_menu_message(bot, user)

    await bot.send_message(update, context, text, keyboard, refresh=True)
    return Dialogs.MENU


async def start_menu_dialog(update: "Update", context: "ContextTypes.DEFAULT_TYPE", bot: "Bot") -> int:
    return await show_main_menu(update, context, bot)
