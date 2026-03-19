from copy import deepcopy
from typing import TYPE_CHECKING

from shared.entities.dialog_option import Option
from shared.constants import Dialogs, Actions, Variables

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes
    from bot import Bot

PROFILE_OBJECT_ITEM_ID = 5
PROFILE_OBJECT_OPTION_OFFSET = 5000


def build_profile_dialog(base_dialog, objects):
    dialog = deepcopy(base_dialog)
    root_sequence = dialog.sequences.get(0)
    object_item = dialog.items.get(PROFILE_OBJECT_ITEM_ID)

    if root_sequence is None or object_item is None:
        return dialog

    option_ids: list[int] = []
    sorted_objects = sorted(
        [obj for obj in objects if getattr(obj, "id", None) is not None],
        key=lambda obj: (obj.name or "").casefold(),
    )

    for index, obj in enumerate(sorted_objects):
        option_id = PROFILE_OBJECT_OPTION_OFFSET + int(obj.id)
        dialog.options[option_id] = Option(
            id=option_id,
            text=obj.name or f"Object {obj.id}",
            sequence_id=None,
            row=index // 2,
        )
        option_ids.append(option_id)

    object_item.options_ids = option_ids

    if not option_ids:
        root_sequence.items_ids = [
            item_id for item_id in root_sequence.items_ids if item_id != PROFILE_OBJECT_ITEM_ID
        ]

    return dialog


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
    
    bot.managers.navigator.set_entry_point(context, Dialogs.PROFILE)

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
    user_object = ""
    if user.object_id:
        obj = await bot.services.rental_object.get_object_by_id(user.object_id)
        user_object = obj.name if obj else ""
    user_phone = user.phone_number or bot.get_text("phone_not_specified")

    bot.managers.storage.set(context, Variables.USER_NAME, user_name)
    bot.managers.storage.set(context, Variables.USER_OBJECT, user_object)
    bot.managers.storage.set(context, Variables.USER_LEGAL_ENTITY, user.legal_entity or "")

    objects = await bot.services.rental_object.get_all_objects()
    profile_dialog = build_profile_dialog(bot.dyn_dialogs[Dialogs.PROFILE], objects)

    bot.managers.storage.set(context, Variables.ACTIVE_DYN_DIALOG, profile_dialog)
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
        payload=[user_name, user_legal_entity, user_object or bot.get_text("location_not_specified"), user_phone],
        refresh=True
    )
    return Dialogs.PROFILE
