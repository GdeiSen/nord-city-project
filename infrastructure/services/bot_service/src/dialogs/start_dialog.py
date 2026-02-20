from typing import TYPE_CHECKING
from shared.schemas import UserSchema
from shared.constants import Dialogs, Actions, Variables, Roles

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes
    from bot import Bot

async def start_app_dialog(update: "Update", context: "ContextTypes.DEFAULT_TYPE", bot: "Bot") -> None:
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
    if user_id:
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
                role=Roles.LPR
            )
            user = await bot.services.user.create_user(new_user)
            if not user:
                return
        
        if user:
            bot.managers.storage.set(context, Variables.USER_NAME, (
                (user.last_name or "") + " " + (user.first_name or "") + " " + (user.middle_name or "")
            ).strip())
            bot.managers.storage.set(context, Variables.USER_LEGAL_ENTITY, user.legal_entity or "")
    else:
        return

    await bot.send_message(
        update,
        context,
        "data_sync_completed",
        bot.create_keyboard([[("continue", Dialogs.MENU)]])
    )
    return Dialogs.MENU