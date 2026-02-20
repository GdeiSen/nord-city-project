from typing import TYPE_CHECKING
from shared.constants import Dialogs, Variables

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes
    from bot import Bot

async def start_service_feedback_dialog(update: "Update", context: "ContextTypes.DEFAULT_TYPE", bot: "Bot") -> int:
    """
    Начинает диалог обратной связи по заявке после ее выполнения
    """
    ticket_id = None
    
    if context.user_data and 'callback_params' in context.user_data:
        params = context.user_data['callback_params']
        if len(params) > 0:
            try:
                ticket_id = int(params[0])
            except (ValueError, TypeError):
                pass

    bot.managers.navigator.set_entry_point(context, Dialogs.MENU)
    bot.managers.storage.set(context, Variables.USER_SERVICE_TICKET, ticket_id)
    bot.managers.storage.set(context, Variables.ACTIVE_DYN_DIALOG, bot.dyn_dialogs[Dialogs.SERVICE_FEEDBACK])
    bot.managers.storage.set(context, Variables.ACTIVE_DIALOG_SEQUENCE_ID, 0)
    bot.managers.storage.set(context, Variables.ACTIVE_DIALOG_SEQUENCE_ITEM_INDEX, 0)
    await bot.managers.navigator.execute(f"{Dialogs.DYN_DIALOG_ITEM}", update, context)
    