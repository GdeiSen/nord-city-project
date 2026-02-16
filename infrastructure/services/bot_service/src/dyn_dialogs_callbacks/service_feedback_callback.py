from typing import TYPE_CHECKING
from shared.constants import Dialogs, Variables
import json
from datetime import datetime

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes
    from shared.entities.dialog import Dialog
    from bot import Bot

async def service_feedback_callback(
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
    """
    Обработчик обратной связи по выполненной заявке.
    
    Функция обрабатывает различные этапы диалога обратной связи:
    1. Начальный этап (sequence_id = 0):
       - При положительной оценке (option_id = 100) - завершает диалог
       - При отрицательной оценке (option_id = 101) - инициирует сбор деталей
    2. Этап сбора деталей о проблемах качества (sequence_id = 2)
    3. Этап сбора деталей о проблемах скорости (sequence_id = 3)
    4. Этап сбора дополнительных комментариев (sequence_id = 4)
    
    Args:
        bot (Bot): Экземпляр бота
        update (Update): Объект обновления от Telegram
        context (ContextTypes.DEFAULT_TYPE): Контекст обработчика
        dialog (Dialog): Текущий диалог
        sequence_id (int): ID текущей последовательности в диалоге
        item_id (int): ID текущего элемента в последовательности
        option_id (int | None): ID выбранной опции
        answer (str | None): Текстовый ответ пользователя
        state (int): Текущее состояние диалога
    
    Returns:
        int | str: Следующее состояние диалога или код завершения
    """
    # Получаем ID заявки из локального хранилища
    ticket_id = bot.managers.storage.get(context, Variables.USER_SERVICE_TICKET)
    
    # Обработка начального этапа диалога
    if sequence_id == 0 and item_id == 0:
        if option_id == 100 and state == True:
            # При положительной оценке завершаем диалог
            await bot.send_message(update, context, "service_feedback_thanks", dynamic=False)
            return await bot.managers.router.execute(Dialogs.MENU, update, context)
        elif option_id == 101:
            # При отрицательной оценке очищаем предыдущее сообщение
            bot.managers.storage.set(context, "feedback_message", "")
            
    # Обработка этапа сбора деталей о проблемах качества
    elif sequence_id == 1 and item_id == 1:
        if option_id == 201 and state == True:
        # Сохраняем сообщение о проблемах качества
            bot.managers.storage.set(context, "feedback_message", bot.get_text('service_feedback_quality_problems'))
            if ticket_id:
                # Отправляем обратную связь главному инженеру через NotificationManager
                await bot.services.notification.send_feedback_to_chief_engineer(
                    ticket_id, bot.get_text('service_feedback_quality_problems')
                )
                await bot.send_message(
                    update, 
                    context, 
                    "service_feedback_sent_to_engineer", 
                    dynamic=False,
                )
            return await bot.managers.router.execute(Dialogs.MENU, update, context)
        elif option_id == 202 and state == True:
            # Сохраняем сообщение о проблемах скорости
            bot.managers.storage.set(context, "feedback_message", bot.get_text('service_feedback_speed_problems'))
            if ticket_id:
                # Отправляем обратную связь главному инженеру через NotificationManager
                await bot.services.notification.send_feedback_to_chief_engineer(
                    ticket_id, bot.get_text('service_feedback_speed_problems')
                )
            await bot.send_message(
                update, 
                context, 
                "service_feedback_sent_to_engineer", 
                dynamic=False,
            )
            return await bot.managers.router.execute(Dialogs.MENU, update, context)
        
    # Обработка этапа сбора дополнительных комментариев
    elif sequence_id == 4 and item_id == 4:
        if answer:
            # Сохраняем и отправляем дополнительные комментарии
            bot.managers.storage.set(context, "feedback_message", f"{bot.get_text('service_feedback_quality_problems')}: {answer}")
            if ticket_id:
                await bot.services.notification.send_feedback_to_chief_engineer(
                    ticket_id, f"{bot.get_text('service_feedback_quality_problems')}: {answer}"
                )
            await bot.send_message(
                update, 
                context, 
                "service_feedback_sent_to_engineer", 
                dynamic=False,
            )

 