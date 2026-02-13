# from typing import TYPE_CHECKING
# from shared.constants import Actions

# if TYPE_CHECKING:
#     from telegram import Update
#     from telegram.ext import ContextTypes
#     from bot import Bot

# async def start_dyn_dialog(update: "Update", context: "ContextTypes.DEFAULT_TYPE", bot: "Bot") -> int | str:
#     """
#     Entry point for dynamic dialogs.
#     Delegates all processing to the DynDialogService.
#     """
#     if update.effective_chat.type != "private":
#         return Actions.END
        
#     # Delegate all complex logic to the dedicated service
#     return await bot.services.dyn_dialog.process_step(update, context)


from typing import TYPE_CHECKING
from shared.constants import Dialogs, Actions, Variables
import logging
if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes
    from bot import Bot


async def start_dyn_dialog(update: "Update", context: "ContextTypes.DEFAULT_TYPE", bot: "Bot") -> int | str:
    if update.effective_chat.type != "private":
        return Actions.END
        
    dialog = bot.managers.storage.get(context, Variables.ACTIVE_DYN_DIALOG)
    if dialog is None:
        return Actions.END
    sequences = dialog.sequences
    items = dialog.items
    options = dialog.options
    dialog_id = dialog.id
    active_sequence_id = bot.managers.storage.get(context, Variables.ACTIVE_DIALOG_SEQUENCE_ID) or 0
    active_sequence_item_index = bot.managers.storage.get(context, Variables.ACTIVE_DIALOG_SEQUENCE_ITEM_INDEX) or 0
    option_id = None
    is_finished = False
    go_back = False
    if update.callback_query and update.callback_query.data is not None:
        callback_data = update.callback_query.data.split(":")
        if callback_data[0] == str(Dialogs.DYN_DIALOG_ITEM) and len(callback_data) > 1 and callback_data[1] == "-1":
            go_back = True
            # Если в кнопке назад есть информация о диалоге и последовательности, сохраняем ее
            if len(callback_data) > 2:
                callback_dialog_id = int(callback_data[2])
                if len(callback_data) > 3:
                    callback_sequence_id = int(callback_data[3])
                if len(callback_data) > 4:
                    callback_item_id = int(callback_data[4])
            bot.managers.router.pop_previous_trace_item(context)
        elif len(callback_data) > 1:
            try:
                # Новый формат: диалог:последовательность:элемент:опция
                callback_dialog_id = int(callback_data[1])
                if len(callback_data) > 2:
                    callback_sequence_id = int(callback_data[2])
                if len(callback_data) > 3:
                    callback_item_id = int(callback_data[3])
                if len(callback_data) > 4:
                    option_id = int(callback_data[4])
            except ValueError:
                option_id = None
                callback_dialog_id = None
                
    handled_data = bot.managers.storage.get(context, Variables.HANDLED_DATA)
    if handled_data is not None:
        bot.managers.storage.set(context, Variables.HANDLED_DATA, None)
    active_sequence = sequences.get(active_sequence_id)
    if not active_sequence or not active_sequence.items_ids:
        active_sequence_id = 0
        active_sequence_item_index = 0
        active_sequence = sequences.get(0)
        if not active_sequence:
            raise ValueError("No active sequence found")  
    if go_back:
        trace = bot.managers.router.get_current_trace(context)
        if trace and len(trace) > 1:
            bot.managers.router.pop_previous_trace_item(context)
            trace = bot.managers.router.get_current_trace(context)
            if trace and len(trace) == 1:
                return await bot.managers.router.execute_entry_point_item(update, context)
            prev_item = bot.managers.router.get_current_trace_item(context)
            if isinstance(prev_item, str) and ":" in prev_item:
                trace_parts = prev_item.split(":")
                if len(trace_parts) >= 4:
                    active_sequence_id = int(trace_parts[2])
                    item_id = int(trace_parts[3])
                    
                    # Проверяем, есть ли option_id в трейсе
                    # if len(trace_parts) > 4:
                    #     try:
                    #         option_id = int(trace_parts[4])
                    #     except (ValueError, IndexError):
                    #         option_id = None
                    
                    active_sequence = sequences.get(active_sequence_id)
                    if active_sequence and item_id in active_sequence.items_ids:
                        active_sequence_item_index = active_sequence.items_ids.index(item_id)
                    else:
                        active_sequence_item_index = 0
                    
                    bot.managers.storage.set(context, Variables.ACTIVE_DIALOG_SEQUENCE_ID, active_sequence_id)
                    bot.managers.storage.set(context, Variables.ACTIVE_DIALOG_SEQUENCE_ITEM_INDEX, active_sequence_item_index)
        if trace and len(trace) == 1:
            return await bot.managers.router.execute_entry_point_item(update, context)
    active_items = [items[i] for i in active_sequence.items_ids if i in items]
    
    if not active_items:
        bot.managers.storage.set(context, Variables.ACTIVE_DYN_DIALOG, None)
        return await bot.managers.router.execute_entry_point_item(update, context)
        
    if active_sequence_item_index >= len(active_items):
        active_sequence_item_index = 0
    
    active_item = active_items[active_sequence_item_index]
    current_item_id = active_sequence.items_ids[active_sequence_item_index]
    # Вспомогательная функция для вызова обработчика с общими параметрами
    async def handle_dialog(is_dialog_finished=False, update_sequence_data=True):
        nonlocal active_sequence_id, active_sequence_item_index, active_sequence
        await bot.dyn_dialog_handlers_manager.handle(
            dialog_id,
            bot,
            update,
            context,
            dialog,
            active_sequence.id,
            active_item.id,
            option_id,
            handled_data,
            is_dialog_finished
        )
        
        if update_sequence_data:
            active_sequence_id = bot.managers.storage.get(context, Variables.ACTIVE_DIALOG_SEQUENCE_ID)
            active_sequence_item_index = bot.managers.storage.get(context, Variables.ACTIVE_DIALOG_SEQUENCE_ITEM_INDEX) or 0
            active_sequence = sequences.get(active_sequence_id) 
    if option_id is not None and handled_data is None:
        selected_option = options.get(option_id)
        if selected_option is not None and selected_option.sequence_id is not None:
            bot.managers.storage.set(context, Variables.ACTIVE_DIALOG_SEQUENCE_ID, selected_option.sequence_id)
            bot.managers.storage.set(context, Variables.ACTIVE_DIALOG_SEQUENCE_ITEM_INDEX, 0)
            await handle_dialog()
            active_sequence_item_index = 0
        else:
            if active_sequence_item_index + 1 < len(active_items):
                bot.managers.storage.set(context, Variables.ACTIVE_DIALOG_SEQUENCE_ITEM_INDEX, active_sequence_item_index + 1)
                active_sequence_item_index += 1
            elif active_sequence.next_sequence_id is not None:
                bot.managers.storage.set(context, Variables.ACTIVE_DIALOG_SEQUENCE_ID, active_sequence.next_sequence_id)
                bot.managers.storage.set(context, Variables.ACTIVE_DIALOG_SEQUENCE_ITEM_INDEX, 0)
                active_sequence_id = active_sequence.next_sequence_id
                active_sequence_item_index = 0
                active_sequence = sequences.get(active_sequence_id)
            else:
                bot.managers.storage.set(context, Variables.ACTIVE_DYN_DIALOG, None)
                await handle_dialog(is_dialog_finished=True, update_sequence_data=False)
            
            await handle_dialog()     
    elif handled_data is not None: 
        if not go_back:
            if active_sequence_item_index + 1 < len(active_items):
                bot.managers.storage.set(context, Variables.ACTIVE_DIALOG_SEQUENCE_ITEM_INDEX, active_sequence_item_index + 1)
            elif active_sequence.next_sequence_id is not None:
                bot.managers.storage.set(context, Variables.ACTIVE_DIALOG_SEQUENCE_ID, active_sequence.next_sequence_id)
                bot.managers.storage.set(context, Variables.ACTIVE_DIALOG_SEQUENCE_ITEM_INDEX, 0)
            else:
                # Диалог завершен, очищаем данные перед переходом в меню
                await handle_dialog(is_dialog_finished=True, update_sequence_data=False)
                bot.managers.storage.set(context, Variables.ACTIVE_DYN_DIALOG, None)
                bot.managers.storage.set(context, Variables.ACTIVE_DIALOG_TRACE, [])
                return await bot.managers.router.execute_entry_point_item(update, context)

        await handle_dialog()
    
    # Если диалог был очищен в handle_dialog, то выходим
    if bot.managers.storage.get(context, Variables.ACTIVE_DYN_DIALOG) is None:
        return await bot.managers.router.execute_entry_point_item(update, context)
        
    active_items = [items[i] for i in active_sequence.items_ids if i in items]
    active_item = active_items[active_sequence_item_index]
    current_item_id = active_sequence.items_ids[active_sequence_item_index]
    trace_data = f"{Dialogs.DYN_DIALOG_ITEM}:{dialog_id}:{active_sequence_id}:{current_item_id}"
    if option_id is not None:
        trace_data = f"{trace_data}:{option_id}"
    bot.managers.router.edit_current_trace_item(context, trace_data)
    
    # Исправление ошибки list index out of range
    current_trace = bot.managers.router.get_current_trace(context)
    if current_trace and len(current_trace) >= 2 and current_trace[-2] == trace_data:
        bot.managers.router.pop_previous_trace_item(context)
    
    if active_item.type == 0:
        active_options = [options[i] for i in (active_item.options_ids or []) if i in options]
        
        options_by_row = {}
        for option in active_options:
            if option.row not in options_by_row:
                options_by_row[option.row] = []
            
            # Проверяем, есть ли пользовательский callback_data
            if hasattr(option, 'callback_data') and option.callback_data is not None:
                callback_data = option.callback_data
            else:
                # Стандартный формат callback_data
                callback_data = f"{Dialogs.DYN_DIALOG_ITEM}:{dialog_id}:{active_sequence_id}:{current_item_id}:{option.id}"
            
            options_by_row[option.row].append((option.text, callback_data))
    
        keyboard_rows = []
        for row in sorted(options_by_row.keys()):
            keyboard_rows.append(options_by_row[row])
            
        # Кнопка назад должна использовать общий формат
        back_data = f"{Dialogs.DYN_DIALOG_ITEM}:-1:{dialog_id}:{active_sequence_id}:{current_item_id}"
        keyboard_rows.append([("back", back_data)])
    
        keyboard = bot.create_keyboard(keyboard_rows)
        
        # Получаем изображения из активного элемента
        images = getattr(active_item, 'images', None)
    
        await bot.send_message(
            update, context, "multi_dialog_item_select_handler_prompt", keyboard, 
            payload=[active_item.text], images=images
        )
        return None
        
    elif active_item.type == 1:
        async def text_received_handler(text_update: "Update", text_context: "ContextTypes.DEFAULT_TYPE"):
            return await bot.managers.router.execute(Dialogs.DYN_DIALOG_ITEM, text_update, text_context)
        
        user_id = bot.get_user_id(update)
        if user_id:
            bot.managers.event.register_input_handler(user_id, Actions.TYPING, text_received_handler)
        
        # Кнопка назад должна использовать общий формат
        back_data = f"{Dialogs.DYN_DIALOG_ITEM}:-1:{dialog_id}:{active_sequence_id}:{current_item_id}"
        keyboard = bot.create_keyboard([[("back", back_data)]])
            
        await bot.send_message(
            update, context, "multi_dialog_item_text_handler_prompt", keyboard, payload=[active_item.text]
        )
        return None
    
    else:
        trace = bot.managers.router.get_current_trace(context)
        if trace and len(trace) > 1:
            # Кнопка назад должна использовать общий формат
            back_data = f"{Dialogs.DYN_DIALOG_ITEM}:-1:{dialog_id}:{active_sequence_id}:{current_item_id}"
            keyboard = bot.create_keyboard([[("back", back_data)]])
        else:
            keyboard = bot.create_keyboard([[("cancel", Actions.CANCEL)]])

        await bot.send_message(update, context, active_item.text, keyboard)
        return Dialogs.DYN_DIALOG_ITEM
