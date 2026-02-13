from typing import TYPE_CHECKING
from datetime import datetime
from shared.constants import Dialogs, Actions, Variables
from shared.models import Feedback

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes
    from bot import Bot

async def start_feedback_dialog(update: "Update", context: "ContextTypes.DEFAULT_TYPE", bot: "Bot") -> int:

    if update.effective_chat.type != "private":
        return

    bot.managers.router.set_entry_point_item(context, Dialogs.MENU)
    bot.managers.storage.set(context, Variables.ACTIVE_DYN_DIALOG, bot.dyn_dialogs[Dialogs.FEEDBACK])
    bot.managers.storage.set(context, Variables.ACTIVE_DIALOG_SEQUENCE_ID, 0)
    bot.managers.storage.set(context, Variables.ACTIVE_DIALOG_SEQUENCE_ITEM_INDEX, 0)
    return await bot.managers.router.execute(Dialogs.DYN_DIALOG_ITEM, update, context)
