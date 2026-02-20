"""
Утилиты для callback-ов динамических диалогов.

Помогают единообразно управлять позицией (sequence_id, item_index) при
ошибках валидации или необходимости вернуться на предыдущий шаг.
"""
from typing import TYPE_CHECKING

from shared.constants import Variables

if TYPE_CHECKING:
    from telegram.ext import ContextTypes
    from bot import Bot


def set_dialog_position(
    bot: "Bot",
    context: "ContextTypes.DEFAULT_TYPE",
    sequence_id: int,
    item_index: int,
) -> None:
    """
    Установить текущую позицию в динамическом диалоге.

    Используйте при ошибке валидации, чтобы пользователь остался на том же шаге
    и мог повторно ввести данные.

    Example:
        if not is_valid_phone(answer):
            set_dialog_position(bot, context, sequence_id, item_id)
            await bot.send_message(update, context, "phone_validation_error", ...)
            return CallbackResult.retry_current(sequence_id, item_id)
    """
    bot.managers.storage.set(context, Variables.ACTIVE_DIALOG_SEQUENCE_ID, sequence_id)
    bot.managers.storage.set(context, Variables.ACTIVE_DIALOG_SEQUENCE_ITEM_INDEX, item_index)
