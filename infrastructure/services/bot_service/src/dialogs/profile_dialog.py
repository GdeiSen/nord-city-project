from typing import TYPE_CHECKING
from shared.constants import Dialogs, Actions, Variables

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes
    from bot import Bot


async def start_profile_dialog(update: "Update", context: "ContextTypes.DEFAULT_TYPE", bot: "Bot") -> int:
    """
    Handles the user profile dialog for viewing and editing personal information.
    
    This dialog allows users to:
    - View their current profile information (name, legal entity, object)
    - Update their profile through dynamic dialog sequences
    - Navigate back to the main menu
    
    Args:
        update (Update): Telegram update object containing user interaction
        context (ContextTypes.DEFAULT_TYPE): Telegram context for conversation state  
        bot (Bot): Bot instance providing access to services and messaging
    
    Returns:
        int: Dialog constant indicating the profile dialog state
    """
    if update.effective_chat.type != "private":
        return
    
    bot.managers.router.set_entry_point_item(context, Dialogs.PROFILE)

    user_id = bot.get_user_id(update)

    if user_id is None:
        return Actions.END

    user = await bot.services.user.get_user_by_id(user_id)

    if user is None:
        return Actions.END

    last_name = user.last_name or ""
    first_name = user.first_name or ""
    middle_name = user.middle_name or ""

    user_name = last_name + " " + first_name + " " + middle_name
    user_name = user_name.replace("  ", " ")
    user_name = user_name.strip()
    user_legal_entity = user.legal_entity or ""
    user_object = user.object or ""

    bot.managers.storage.set(context, Variables.USER_NAME, user_name)
    bot.managers.storage.set(context, Variables.USER_OBJECT, user.object or "")
    bot.managers.storage.set(context, Variables.USER_LEGAL_ENTITY, user.legal_entity or "")

    bot.managers.storage.set(context, Variables.ACTIVE_DYN_DIALOG, bot.dyn_dialogs[Dialogs.PROFILE])
    bot.managers.storage.set(context, Variables.ACTIVE_DIALOG_SEQUENCE_ID, 0)
    bot.managers.storage.set(context, Variables.ACTIVE_DIALOG_SEQUENCE_ITEM_INDEX, 0)

    await bot.send_message(
        update,
        context,
        "profile_header",
        bot.create_keyboard(
            [
                [("login_repeat", Dialogs.DYN_DIALOG_ITEM)],
                [("back", Dialogs.MENU)],
            ]
        ),
        payload=[user_name, user_legal_entity, user_object],
        refresh=True
    )
    return Dialogs.PROFILE
