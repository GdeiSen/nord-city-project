from typing import TYPE_CHECKING
from shared.constants import Dialogs, Actions, Roles, Variables

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes
    from bot import Bot


async def start_menu_dialog(update: "Update", context: "ContextTypes.DEFAULT_TYPE", bot: "Bot") -> int:
    """
    Displays the main menu dialog with user-specific options based on role and profile completion.
    
    This dialog serves as the central navigation hub, showing different menu options based on:
    - User role (MA, LPR, etc.)
    - Profile completion status
    - User permissions
    
    Args:
        update (Update): Telegram update object containing user interaction
        context (ContextTypes.DEFAULT_TYPE): Telegram context for conversation state
        bot (Bot): Bot instance providing access to services and messaging
    
    Returns:
        int: Dialog constant indicating the menu dialog state
    """
    if update.effective_chat.type != "private":
        return
    
    bot.managers.router.set_entry_point_item(context, Dialogs.MENU)
    user_id = bot.get_user_id(update)

    if user_id is None:
        return Actions.END

    user = await bot.services.user.get_user_by_id(user_id)

    if user is None:
        return Actions.END

    # Store user information in context
    bot.managers.storage.set(context, Variables.USER_NAME, (
        (user.last_name or "") + " " +
        (user.first_name or "") + " " +
        (user.middle_name or "")
    ).strip())
    bot.managers.storage.set(context, Variables.USER_LEGAL_ENTITY, user.legal_entity or "")

    keyboard = bot.create_keyboard(
        [
            [
                ("profile", Dialogs.PROFILE),
                ("service", Dialogs.SERVICE)],
            [
                ("polling", Dialogs.POLL),
                ("feedback", Dialogs.FEEDBACK),
            ],
            [
                ("spaces", Dialogs.SPACES)
            ]
        ]
    )

    text = "default_greeting"

    if user.role == Roles.MA or user.role == Roles.GUEST:
        text = "ma_greeting"
        keyboard = bot.create_keyboard(
            [
                [
                    ("profile",Dialogs.PROFILE),
                    ("service", Dialogs.SERVICE),
                ],
                [
                    ("spaces", Dialogs.SPACES)
                ]
            ]
        )

    if not user.last_name or not user.first_name or not user.middle_name or not user.legal_entity:
        text = "new_greeting"
        keyboard = bot.create_keyboard(
            [
                [
                    ("login", Dialogs.PROFILE)
                ]
            ]
        )

    await bot.send_message(update, context, text, keyboard, refresh = True)
    return Dialogs.MENU
