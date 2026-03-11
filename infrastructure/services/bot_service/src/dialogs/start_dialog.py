import os
from typing import TYPE_CHECKING

from shared.schemas import UserSchema
from shared.constants import Dialogs, Actions, Variables, Roles

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes
    from bot import Bot

START_PAYLOAD_CTX_KEY = "start_payload"
CONSENT_AGREE_CALLBACK = "consent_agree"
CONSENT_EXIT_CALLBACK = "consent_exit"


def _normalize_start_payload(payload: str | None) -> str:
    return (payload or "").strip()


def _resolve_role_from_start_payload(payload: str) -> int | None:
    normalized_payload = payload.casefold()
    if not normalized_payload:
        return None

    lpr_token = os.getenv("BOT_DEEP_LINK_LPR_TOKEN", "lpr").strip().casefold()
    ma_token = os.getenv("BOT_DEEP_LINK_MA_TOKEN", "ma").strip().casefold()

    if lpr_token and normalized_payload == lpr_token:
        return Roles.LPR
    if ma_token and normalized_payload == ma_token:
        return Roles.MA
    return None


def _can_apply_start_role(user_role: int | None) -> bool:
    return user_role in (None, Roles.GUEST, Roles.LPR, Roles.MA)


def _save_user_context(context: "ContextTypes.DEFAULT_TYPE", bot: "Bot", user: UserSchema) -> None:
    bot.managers.storage.set(
        context,
        Variables.USER_NAME,
        ((user.last_name or "") + " " + (user.first_name or "") + " " + (user.middle_name or "")).strip(),
    )
    bot.managers.storage.set(context, Variables.USER_LEGAL_ENTITY, user.legal_entity or "")


async def _handle_consent_callback(
    update: "Update",
    context: "ContextTypes.DEFAULT_TYPE",
    bot: "Bot",
) -> int | str:
    user_id = bot.get_user_id(update)
    if user_id is None:
        return Actions.END

    handled_data = bot.managers.storage.get(context, Variables.HANDLED_DATA)
    bot.managers.storage.set(context, Variables.HANDLED_DATA, None)

    if handled_data == CONSENT_AGREE_CALLBACK:
        updated_user = await bot.services.user.update_user(user_id, {"data_processing_consent": True})
        if updated_user is None:
            await bot.send_message(
                update,
                context,
                "Не удалось сохранить согласие. Попробуйте снова командой /start.",
                dynamic=False,
            )
            return Actions.END

        _save_user_context(context, bot, updated_user)
        await bot.managers.navigator.execute(Dialogs.MENU, update, context)
        return Dialogs.MENU

    if handled_data == CONSENT_EXIT_CALLBACK:
        bot.managers.navigator.clear(context)
        await bot.send_message(
            update,
            context,
            "Работа с ботом завершена. Чтобы вернуться, нажмите /start.",
            dynamic=False,
        )
        return Actions.END

    keyboard = bot.create_keyboard(
        [[("agree", CONSENT_AGREE_CALLBACK), ("exit", CONSENT_EXIT_CALLBACK)]]
    )
    await bot.send_message(update, context, "user_agreement_input_handler_prompt", keyboard)
    bot.register_input_handler(user_id, Actions.CALLBACK, _handle_consent_callback)
    return Actions.END


async def start_app_dialog(update: "Update", context: "ContextTypes.DEFAULT_TYPE", bot: "Bot") -> int | str:
    """
    Handles the initial bot interaction and user registration/authentication.
    
    This function processes the /start command and manages the complete user
    onboarding flow. It handles both new user registration and existing user
    authentication, setting up the user's session and profile data.
    
    Process Flow:
    1. Extracts user information from Telegram update
    2. Checks if user exists in database
    3. For new users: creates account with Telegram data
    4. For existing users: updates last activity
    5. Sets up user session variables
    6. Redirects to main menu
    
    Args:
        update (Update): Telegram update containing user interaction
        context (ContextTypes.DEFAULT_TYPE): Telegram context for session management
        bot (Bot): Main bot instance with access to services and managers
        
    Raises:
        Exception: Logs errors during user creation or database operations
    """
    user_id = bot.get_user_id(update)
    if user_id is None:
        return Actions.END

    raw_start_payload = context.user_data.get(START_PAYLOAD_CTX_KEY) if context.user_data is not None else ""
    start_payload = _normalize_start_payload(raw_start_payload)
    start_role = _resolve_role_from_start_payload(start_payload)

    user = await bot.services.user.get_user_by_id(user_id)
    if user is None:
        telegram_user = update.effective_user
        new_user = UserSchema(
            id=user_id,
            username=telegram_user.username or "",
            first_name=telegram_user.first_name or "",
            last_name=telegram_user.last_name or "",
            object_id=1,
            middle_name="",
            legal_entity="",
            role=start_role or Roles.LPR,
            data_processing_consent=False,
        )
        user = await bot.services.user.create_user(new_user)
        if user is None:
            return Actions.END
    elif start_role is not None and start_role != user.role and _can_apply_start_role(user.role):
        updated_user = await bot.services.user.update_user(user_id, {"role": start_role})
        if updated_user is not None:
            user = updated_user

    _save_user_context(context, bot, user)

    if not user.data_processing_consent:
        keyboard = bot.create_keyboard(
            [[("agree", CONSENT_AGREE_CALLBACK), ("exit", CONSENT_EXIT_CALLBACK)]]
        )
        await bot.send_message(update, context, "user_agreement_input_handler_prompt", keyboard)
        bot.register_input_handler(user_id, Actions.CALLBACK, _handle_consent_callback)
        return Actions.END

    await bot.send_message(
        update,
        context,
        "data_sync_completed",
        bot.create_keyboard([[("continue", Dialogs.MENU)]]),
    )
    return Dialogs.MENU
