from typing import TYPE_CHECKING
from shared.constants import Dialogs, Variables

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes
    from bot import Bot


async def start_service_dialog(update: "Update", context: "ContextTypes.DEFAULT_TYPE", bot: "Bot") -> int:
    
    if update.effective_chat.type != "private":
        return
    
    bot.managers.navigator.set_entry_point(context, Dialogs.SERVICE)
    bot.managers.storage.set(context, Variables.ACTIVE_DYN_DIALOG, bot.dyn_dialogs[Dialogs.SERVICE])
    bot.managers.storage.set(context, Variables.ACTIVE_DIALOG_SEQUENCE_ID, 0)
    bot.managers.storage.set(context, Variables.ACTIVE_DIALOG_SEQUENCE_ITEM_INDEX, 0)
    await bot.send_message(
        update,
        context,
        "service_header",
        bot.create_keyboard(
            [
                [("start", Dialogs.DYN_DIALOG_ITEM)],
                [("back", Dialogs.MENU)],
            ]
        ),
        payload=["-", "-", "-"],
    )
    return Dialogs.SERVICE
