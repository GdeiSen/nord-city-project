from typing import TYPE_CHECKING
from shared.constants import Dialogs, Variables, CallbackResult

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes
    from bot import Bot
    from shared.entities.dialog import Dialog

from shared.constants import Variables
from utils.dyn_dialog_utils import set_dialog_position
from dyn_dialogs_callbacks.guest_parking_callback import (
    is_valid_belarus_phone,
    _normalize_phone,
)


def is_valid_name(name: str) -> bool:
    return name.isalpha() and len(name) < 30 and " " not in name

async def profile_callback(
    bot: "Bot",
    update: "Update",
    context: "ContextTypes.DEFAULT_TYPE",
    dialog: "Dialog",
    sequence_id: "int",
    item_id: "int",
    option_id: "int | None",
    answer: "str | None",
    state: "int",
) -> int | str:

    user_id = bot.get_user_id(update)

    if user_id:
        user = await bot.services.user.get_user_by_id(user_id)

        if user:
            update_data = None
            if item_id in {0, 1, 2}:
                if not is_valid_name(answer or ""):
                    active_seq = dialog.sequences.get(sequence_id)
                    idx = active_seq.items_ids.index(item_id) if active_seq and item_id in active_seq.items_ids else item_id
                    set_dialog_position(bot, context, sequence_id, idx)
                    await bot.send_message(
                        update,
                        context,
                        "profile_name_validation_error",
                        dynamic=False
                    )
                    return CallbackResult.retry_current(sequence_id, idx)

                update_data = {'id': user_id}
                if item_id == 0:
                    update_data['first_name'] = answer
                elif item_id == 1:
                    update_data['last_name'] = answer
                elif item_id == 2:
                    update_data['middle_name'] = answer
            elif item_id == 3:
                update_data = {'id': user_id, 'legal_entity': answer}
            elif item_id == 4:
                if option_id == 4000:
                    update_data = {'id': user_id, 'phone_number': None}
                elif not is_valid_belarus_phone(answer or ""):
                    active_seq = dialog.sequences.get(sequence_id)
                    idx = active_seq.items_ids.index(item_id) if active_seq and item_id in active_seq.items_ids else item_id
                    set_dialog_position(bot, context, sequence_id, idx)
                    await bot.send_message(
                        update,
                        context,
                        "profile_phone_validation_error",
                        dynamic=False
                    )
                    return CallbackResult.retry_current(sequence_id, idx)

                else:
                    update_data = {'id': user_id, 'phone_number': _normalize_phone(answer or "")}

            if update_data is not None:
                updated_user = await bot.services.user.update_user(user_id, update_data)
            else:
                updated_user = None
            if updated_user:
                user = updated_user  # Use updated data

            bot.managers.storage.set(context, Variables.USER_NAME, (
                (user.last_name or "") + " " +
                (user.first_name or "") + " " +
                (user.middle_name or "")
            ).strip())
            bot.managers.storage.set(context, Variables.USER_LEGAL_ENTITY, user.legal_entity or "")

    if state == 1:
        await bot.send_message(update, context, "profile_completed", dynamic=False)
        return await bot.managers.navigator.execute(Dialogs.MENU, update, context)

    return CallbackResult.continue_()
