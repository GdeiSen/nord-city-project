from typing import TYPE_CHECKING
from shared.constants import Dialogs, Variables
from services.rental_space_service import RentalSpaceService  # Using service layer
from services.rental_object_service import RentalObjectService
from utils.spaces_dialog_generator import SpacesDialogGenerator

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes
    from bot import Bot


async def start_spaces_dialog(update: "Update", context: "ContextTypes.DEFAULT_TYPE", bot: "Bot") -> int:
    """
    Диалог для просмотра свободных помещений в объектах недвижимости.
    
    Args:
        update: Объект обновления от Telegram
        context: Контекст обработчика
        bot: Экземпляр бота
    
    Returns:
        int: ID диалога
    """
    if update.effective_chat.type != "private":
        return
    
    bot.managers.navigator.set_entry_point(context, Dialogs.MENU)

    rental_spaces_service: RentalSpaceService = bot.services.rental_space
    rental_object_service: RentalObjectService = bot.services.rental_object
    rental_dialog_generator = SpacesDialogGenerator(bot, rental_spaces_service, rental_object_service)
    dialog = await rental_dialog_generator.generate_dialog()
    
    if dialog:
        bot.dyn_dialogs[Dialogs.SPACES] = dialog
        bot.managers.storage.set(context, Variables.ACTIVE_DYN_DIALOG, dialog)
        bot.managers.storage.set(context, Variables.ACTIVE_DIALOG_SEQUENCE_ID, 0)
        bot.managers.storage.set(context, Variables.ACTIVE_DIALOG_SEQUENCE_ITEM_INDEX, 0)
        return await bot.managers.navigator.execute(Dialogs.DYN_DIALOG_ITEM, update, context)
    else:
        await bot.send_message(
            update,
            context,
            "spaces_error_message",
            bot.create_keyboard(
                [
                    [("back", Dialogs.MENU)],
                ]
            ),
        )
    
    return Dialogs.SPACES 