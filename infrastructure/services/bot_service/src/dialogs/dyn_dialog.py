"""
Обработчик динамических диалогов (dyn_dialog).
Управляет навигацией по графу sequences/items/options из JSON.
"""
from typing import TYPE_CHECKING

from shared.constants import (
    Dialogs,
    Actions,
    Variables,
    DialogCallbackResult,
    DynDialogItemType,
    CallbackResult,
    CallbackActionResult,
)
from shared.entities.route import DDIDRoute

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes
    from bot import Bot


def _build_ddid_trace(dialog_id: int, sequence_id: int, item_id: int, option_id: int | None = None) -> str:
    """DDID-строка для записи в trace."""
    ddid = DDIDRoute(
        route_id=Dialogs.DYN_DIALOG_ITEM,
        dialog_id=dialog_id,
        sequence_id=sequence_id,
        item_id=item_id,
        option_id=option_id,
    )
    return ddid.to_storage()


def _build_back_callback(dialog_id: int, sequence_id: int, item_id: int) -> str:
    """Формат callback_data для кнопки «Назад»."""
    return f"{Dialogs.DYN_DIALOG_ITEM}:-1:{dialog_id}:{sequence_id}:{item_id}"


def _parse_callback_data(callback_raw: str) -> tuple[bool, int | None]:
    """
    Парсинг callback_data. Возвращает (go_back, option_id).
    go_back=True, если формат "8:-1:...".
    """
    parts = callback_raw.split(":")
    if len(parts) < 2:
        return False, None
    go_back = parts[0] == str(Dialogs.DYN_DIALOG_ITEM) and parts[1] == "-1"
    option_id = None
    if len(parts) >= 5 and not go_back:
        try:
            option_id = int(parts[4])
        except ValueError:
            pass
    return go_back, option_id


def _restore_position_from_trace(bot: "Bot", context: "ContextTypes.DEFAULT_TYPE", sequences: dict, prev_item: int | str) -> tuple[int, int] | None:
    """
    Восстановить (sequence_id, item_id) из элемента trace.
    Возвращает None, если восстановление невозможно.
    """
    if not isinstance(prev_item, str) or ":" not in prev_item:
        return None
    pos = DDIDRoute.parse_trace_position(prev_item)
    if pos is None:
        return None
    seq_id, item_id = pos
    if seq_id not in sequences or item_id not in sequences[seq_id].items_ids:
        return None
    return seq_id, sequences[seq_id].items_ids.index(item_id)


async def _handle_go_back(
    bot: "Bot",
    update: "Update",
    context: "ContextTypes.DEFAULT_TYPE",
    sequences: dict,
) -> int | str | None:
    """
    Обработка нажатия «Назад». Возвращает результат для return или None, если продолжать.
    При вызове из navigator.pop() флаг _dyn_back_from_pop: pop уже сделан, только restore.
    """
    trace = bot.managers.navigator.get_stack(context)
    if not trace or len(trace) <= 1:
        return await bot.managers.navigator.execute_entry_point(update, context)

    from_pop = context.user_data.pop('_dyn_back_from_pop', False)
    if not from_pop:
        bot.managers.navigator.pop_item(context)
    trace = bot.managers.navigator.get_stack(context)

    if not trace or len(trace) == 1:
        return await bot.managers.navigator.execute_entry_point(update, context)

    prev_item = bot.managers.navigator.peek(context)
    restored = _restore_position_from_trace(bot, context, sequences, prev_item)
    if restored is not None:
        seq_id, item_index = restored
        bot.managers.storage.set(context, Variables.ACTIVE_DIALOG_SEQUENCE_ID, seq_id)
        bot.managers.storage.set(context, Variables.ACTIVE_DIALOG_SEQUENCE_ITEM_INDEX, item_index)

    return None


def _remove_duplicate_trace(bot: "Bot", context: "ContextTypes.DEFAULT_TYPE", trace_data: str) -> None:
    """
    Удалить дубликат DDID в trace (когда current и previous совпадают).
    Возникает при некоторых сценариях advancement внутри одной sequence.
    """
    stack = bot.managers.navigator.get_stack(context)
    if len(stack) >= 2 and stack[-2] == trace_data:
        bot.managers.navigator.pop_item(context)


def _is_skip_and_complete(result) -> bool:
    """Проверить, что callback вернул «пропустить и завершить» (новый и legacy формат)."""
    if result is None:
        return False
    if isinstance(result, CallbackResult):
        return result.action == CallbackActionResult.SKIP_AND_COMPLETE
    return result == DialogCallbackResult.SKIP_AND_COMPLETE


def _apply_retry_position(bot: "Bot", context: "ContextTypes.DEFAULT_TYPE", result: CallbackResult) -> None:
    """Применить позицию из RETRY_CURRENT (если callback её указал)."""
    if result.sequence_id is not None and result.item_index is not None:
        from utils.dyn_dialog_utils import set_dialog_position
        set_dialog_position(bot, context, result.sequence_id, result.item_index)


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
    option_id: int | None = None
    go_back = False

    if update.callback_query and update.callback_query.data:
        callback_raw = update.callback_query.data
        go_back, option_id = _parse_callback_data(callback_raw)
        # Back вызывается без push (см. bot.handle_callback), поэтому здесь pop не нужен

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
        user_id = bot.get_user_id(update)
        if user_id:
            bot.managers.event.remove_input_handler(user_id)
        result = await _handle_go_back(bot, update, context, sequences)
        if result is not None:
            return result
        if len(bot.managers.navigator.get_stack(context)) == 1:
            return await bot.managers.navigator.execute_entry_point(update, context)
        # Критично: после restore перечитываем из storage (active_sequence мог быть 98)
        active_sequence_id = bot.managers.storage.get(context, Variables.ACTIVE_DIALOG_SEQUENCE_ID) or 0
        active_sequence_item_index = bot.managers.storage.get(context, Variables.ACTIVE_DIALOG_SEQUENCE_ITEM_INDEX) or 0
        active_sequence = sequences.get(active_sequence_id)
        if not active_sequence or not active_sequence.items_ids:
            active_sequence_id = 0
            active_sequence_item_index = 0
            active_sequence = sequences.get(0)

    active_items = [items[i] for i in active_sequence.items_ids if i in items]
    if not active_items:
        bot.managers.storage.set(context, Variables.ACTIVE_DYN_DIALOG, None)
        return await bot.managers.navigator.execute_entry_point(update, context)

    if active_sequence_item_index >= len(active_items):
        active_sequence_item_index = 0

    active_item = active_items[active_sequence_item_index]
    current_item_id = active_sequence.items_ids[active_sequence_item_index]

    async def handle_dialog(is_dialog_finished: bool = False, update_sequence_data: bool = True):
        nonlocal active_sequence_id, active_sequence_item_index, active_sequence
        callback_result = await bot.dyn_dialog_handlers_manager.handle(
            dialog_id, bot, update, context, dialog,
            active_sequence.id, active_item.id, option_id, handled_data, is_dialog_finished
        )
        if update_sequence_data:
            active_sequence_id = bot.managers.storage.get(context, Variables.ACTIVE_DIALOG_SEQUENCE_ID)
            active_sequence_item_index = bot.managers.storage.get(context, Variables.ACTIVE_DIALOG_SEQUENCE_ITEM_INDEX) or 0
            active_sequence = sequences.get(active_sequence_id)
        return callback_result

    # --- Option selected (button click) ---
    if option_id is not None and handled_data is None:
        selected_option = options.get(option_id)
        if selected_option and selected_option.sequence_id is not None:
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
                callback_result = await handle_dialog()
                if _is_skip_and_complete(callback_result):
                    result = await handle_dialog(is_dialog_finished=True, update_sequence_data=False)
                    bot.managers.storage.set(context, Variables.ACTIVE_DYN_DIALOG, None)
                    bot.managers.navigator.clear(context)
                    return result if result is not None else await bot.managers.navigator.execute_entry_point(update, context)
                await handle_dialog(is_dialog_finished=True, update_sequence_data=False)
                await handle_dialog()

    # --- Text/other input (handled_data) ---
    elif handled_data is not None:
        callback_result = None
        if not go_back:
            if active_sequence_item_index + 1 < len(active_items):
                bot.managers.storage.set(context, Variables.ACTIVE_DIALOG_SEQUENCE_ITEM_INDEX, active_sequence_item_index + 1)
            elif active_sequence.next_sequence_id is not None:
                bot.managers.storage.set(context, Variables.ACTIVE_DIALOG_SEQUENCE_ID, active_sequence.next_sequence_id)
                bot.managers.storage.set(context, Variables.ACTIVE_DIALOG_SEQUENCE_ITEM_INDEX, 0)
            else:
                # Последний шаг: обрабатываем ответ, при ошибке валидации — не завершаем
                process_result = await handle_dialog(is_dialog_finished=False, update_sequence_data=True)
                if isinstance(process_result, CallbackResult) and process_result.action == CallbackActionResult.RETRY_CURRENT:
                    _apply_retry_position(bot, context, process_result)
                    callback_result = process_result
                    active_sequence_id = bot.managers.storage.get(context, Variables.ACTIVE_DIALOG_SEQUENCE_ID)
                    active_sequence_item_index = bot.managers.storage.get(context, Variables.ACTIVE_DIALOG_SEQUENCE_ITEM_INDEX) or 0
                    active_sequence = sequences.get(active_sequence_id)
                else:
                    completion_result = await handle_dialog(is_dialog_finished=True, update_sequence_data=False)
                    bot.managers.storage.set(context, Variables.ACTIVE_DYN_DIALOG, None)
                    bot.managers.navigator.clear(context)
                    return completion_result if completion_result is not None else await bot.managers.navigator.execute_entry_point(update, context)

        if callback_result is None:
            callback_result = await handle_dialog()

        if isinstance(callback_result, CallbackResult) and callback_result.action == CallbackActionResult.RETRY_CURRENT:
            _apply_retry_position(bot, context, callback_result)

        if _is_skip_and_complete(callback_result):
            completion_result = await handle_dialog(is_dialog_finished=True, update_sequence_data=False)
            bot.managers.storage.set(context, Variables.ACTIVE_DYN_DIALOG, None)
            bot.managers.navigator.clear(context)
            return completion_result if completion_result is not None else await bot.managers.navigator.execute_entry_point(update, context)

    if bot.managers.storage.get(context, Variables.ACTIVE_DYN_DIALOG) is None:
        return await bot.managers.navigator.execute_entry_point(update, context)

    active_items = [items[i] for i in active_sequence.items_ids if i in items]
    active_item = active_items[active_sequence_item_index]
    current_item_id = active_sequence.items_ids[active_sequence_item_index]

    trace_data = _build_ddid_trace(dialog_id, active_sequence_id, current_item_id, option_id)
    bot.managers.navigator.replace_current(context, trace_data)
    _remove_duplicate_trace(bot, context, trace_data)

    back_data = _build_back_callback(dialog_id, active_sequence_id, current_item_id)

    if active_item.type == DynDialogItemType.SELECT:
        return await _render_select_item(bot, update, context, active_item, options, dialog_id, active_sequence_id, current_item_id, back_data)
    if active_item.type == DynDialogItemType.TEXT_INPUT:
        return await _render_text_item(
            bot, update, context, active_item, back_data,
            options=options, dialog_id=dialog_id, sequence_id=active_sequence_id, item_id=current_item_id
        )
    return await _render_other_item(bot, update, context, active_item, back_data)


async def _render_select_item(
    bot: "Bot",
    update: "Update",
    context: "ContextTypes.DEFAULT_TYPE",
    active_item,
    options: dict,
    dialog_id: int,
    sequence_id: int,
    item_id: int,
    back_data: str,
) -> None:
    """Рендер элемента выбора (кнопки)."""
    active_options = [options[i] for i in (active_item.options_ids or []) if i in options]
    options_by_row: dict[int, list] = {}
    for option in active_options:
        options_by_row.setdefault(option.row, [])
        cb = (
            option.callback_data
            if getattr(option, "callback_data", None)
            else _build_ddid_trace(dialog_id, sequence_id, item_id, option.id)
        )
        options_by_row[option.row].append((option.text, cb))
    keyboard_rows = [options_by_row[r] for r in sorted(options_by_row)]
    if not (dialog_id == Dialogs.GUEST_PARKING and item_id == 106):
        keyboard_rows.append([("back", back_data)])
    keyboard = bot.create_keyboard(keyboard_rows)
    item_text = bot.get_text(active_item.text)
    images = getattr(active_item, "images", None)
    await bot.send_message(update, context, "multi_dialog_item_select_handler_prompt", keyboard, payload=[item_text], images=images)
    return None


async def _render_text_item(
    bot: "Bot",
    update: "Update",
    context: "ContextTypes.DEFAULT_TYPE",
    active_item,
    back_data: str,
    options: dict | None = None,
    dialog_id: int | None = None,
    sequence_id: int | None = None,
    item_id: int | None = None,
) -> None:
    """Рендер элемента ввода текста. При наличии options_ids добавляет кнопки опций (напр. «Удалить номер»)."""
    async def text_handler(text_upd: "Update", text_ctx: "ContextTypes.DEFAULT_TYPE"):
        return await bot.managers.navigator.execute(Dialogs.DYN_DIALOG_ITEM, text_upd, text_ctx)

    user_id = bot.get_user_id(update)
    if user_id:
        bot.managers.event.register_input_handler(user_id, Actions.TYPING, text_handler)

    keyboard_rows = []
    if options and getattr(active_item, "options_ids", None):
        for opt_id in active_item.options_ids:
            if opt_id in options:
                opt = options[opt_id]
                cb = (
                    getattr(opt, "callback_data", None)
                    or (_build_ddid_trace(dialog_id or 0, sequence_id or 0, item_id or 0, opt_id) if dialog_id is not None else None)
                )
                if cb:
                    keyboard_rows.append([(bot.get_text(opt.text), cb)])
    keyboard_rows.append([("back", back_data)])
    keyboard = bot.create_keyboard(keyboard_rows)

    item_text = bot.get_text(active_item.text)
    await bot.send_message(update, context, "multi_dialog_item_text_handler_prompt", keyboard, payload=[item_text])
    return None


async def _render_other_item(
    bot: "Bot",
    update: "Update",
    context: "ContextTypes.DEFAULT_TYPE",
    active_item,
    back_data: str,
) -> int:
    """Рендер прочих элементов."""
    trace = bot.managers.navigator.get_stack(context)
    keyboard = bot.create_keyboard([[("back", back_data)]]) if trace and len(trace) > 1 else bot.create_keyboard([[("cancel", Actions.CANCEL)]])
    await bot.send_message(update, context, active_item.text, keyboard)
    return Dialogs.DYN_DIALOG_ITEM
