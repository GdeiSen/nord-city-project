"""
Callback для диалога гостевой парковки.
Валидация даты, времени (9:00-19:00), госномера, телефонов.
Создание заявки, уведомление администраторов, напоминание за 15 мин.
"""
import re
from datetime import datetime
from typing import TYPE_CHECKING

from shared.constants import Dialogs, Variables, CallbackResult
from utils.time_utils import now

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes
    from bot import Bot
    from shared.entities.dialog import Dialog

from utils.dyn_dialog_utils import set_dialog_position

# Беларусь: +375XXXXXXXXX, 80XXXXXXXXX, 8 0XX XXX XX XX, с пробелами/скобками/тире
_PHONE_REGEX = re.compile(
    r"^[\s\-\(\)]*(?:\+375|80|8\s*0)([\s\-\(\)]*\d){9}[\s\-\(\)]*$"
)


def _normalize_phone(s: str) -> str:
    """Приводит номер к формату +375XXXXXXXXX."""
    digits = re.sub(r"\D", "", s)
    if digits.startswith("80") and len(digits) == 11:
        return "+375" + digits[2:]
    if digits.startswith("8") and len(digits) == 11:
        return "+375" + digits[1:]
    if digits.startswith("375") and len(digits) == 12:
        return "+" + digits
    if len(digits) == 9:
        return "+375" + digits
    return s


def is_valid_belarus_phone(text: str) -> bool:
    """Проверка номера Беларуси (80, +375, скобки, пробелы, тире)."""
    if not text or not text.strip():
        return False
    return bool(_PHONE_REGEX.match(text.strip()))


def _parse_date(s: str) -> datetime | None:
    """Парсит дату в форматах DD.MM.YYYY, DD/MM/YYYY, YYYY-MM-DD."""
    s = (s or "").strip()
    for fmt in ("%d.%m.%Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _parse_time(s: str) -> tuple[int, int] | None:
    """Парсит время, возвращает (hour, minute) или None."""
    s = (s or "").strip().replace(",", ".")
    for fmt in ("%H:%M", "%H.%M", "%H %M"):
        try:
            t = datetime.strptime(s, fmt)
            return t.hour, t.minute
        except ValueError:
            continue
    return None


def _is_time_in_range(hour: int, minute: int) -> bool:
    """Проверка: время в диапазоне 9:00–19:00."""
    if hour < 9:
        return False
    if hour > 19:
        return False
    if hour == 19 and minute > 0:
        return False
    return True


async def guest_parking_callback(
    bot: "Bot",
    update: "Update",
    context: "ContextTypes.DEFAULT_TYPE",
    dialog: "Dialog",
    sequence_id: int,
    item_id: int,
    option_id: int | None,
    answer: str | None,
    state: int,
) -> int | str:
    data: dict = bot.managers.storage.get(context, Variables.GUEST_PARKING_DATA) or {}

    def _idx() -> int:
        active_seq = dialog.sequences.get(sequence_id)
        return active_seq.items_ids.index(item_id) if active_seq and item_id in active_seq.items_ids else 0

    # --- Ввод даты ---
    if item_id == 100:
        parsed = _parse_date(answer or "")
        if not parsed:
            set_dialog_position(bot, context, sequence_id, _idx())
            await bot.send_message(
                update, context, "guest_parking_date_invalid", dynamic=False
            )
            return CallbackResult.retry_current(sequence_id, _idx())
        data["arrival_date"] = parsed
        bot.managers.storage.set(context, Variables.GUEST_PARKING_DATA, data)
        return CallbackResult.continue_()

    # --- Ввод времени ---
    if item_id == 101:
        parsed = _parse_time(answer or "")
        if not parsed:
            set_dialog_position(bot, context, sequence_id, _idx())
            await bot.send_message(
                update, context, "guest_parking_time_invalid", dynamic=False
            )
            return CallbackResult.retry_current(sequence_id, _idx())
        hour, minute = parsed
        if not _is_time_in_range(hour, minute):
            set_dialog_position(bot, context, sequence_id, _idx())
            await bot.send_message(
                update, context, "guest_parking_time_error", dynamic=False
            )
            return CallbackResult.retry_current(sequence_id, _idx())
        data["arrival_time"] = f"{hour:02d}:{minute:02d}"
        data.setdefault("arrival_date", datetime.now())
        bot.managers.storage.set(context, Variables.GUEST_PARKING_DATA, data)
        return CallbackResult.continue_()

    # --- Госномер ---
    if item_id == 102:
        plate = (answer or "").strip()
        if not plate or len(plate) < 2:
            set_dialog_position(bot, context, sequence_id, _idx())
            await bot.send_message(
                update, context, "guest_parking_license_invalid", dynamic=False
            )
            return CallbackResult.retry_current(sequence_id, _idx())
        data["license_plate"] = plate
        bot.managers.storage.set(context, Variables.GUEST_PARKING_DATA, data)
        return CallbackResult.continue_()

    # --- Марка и цвет ---
    if item_id == 103:
        car = (answer or "").strip()
        if not car:
            set_dialog_position(bot, context, sequence_id, _idx())
            await bot.send_message(
                update, context, "guest_parking_car_invalid", dynamic=False
            )
            return CallbackResult.retry_current(sequence_id, _idx())
        data["car_make_color"] = car
        bot.managers.storage.set(context, Variables.GUEST_PARKING_DATA, data)
        return CallbackResult.continue_()

    # --- Телефон водителя ---
    if item_id == 104:
        if not is_valid_belarus_phone(answer or ""):
            set_dialog_position(bot, context, sequence_id, _idx())
            await bot.send_message(
                update, context, "guest_parking_driver_phone_error", dynamic=False
            )
            return CallbackResult.retry_current(sequence_id, _idx())
        data["driver_phone"] = _normalize_phone(answer or "")
        bot.managers.storage.set(context, Variables.GUEST_PARKING_DATA, data)

        user_id = bot.get_user_id(update)
        user = await bot.services.user.get_user_by_id(user_id) if user_id else None
        if user and user.phone_number and user.phone_number.strip():
            # У арендатора уже есть контакт — переходим к финалу
            data["tenant_phone"] = _normalize_phone(user.phone_number)
            bot.managers.storage.set(context, Variables.GUEST_PARKING_DATA, data)
            bot.managers.storage.set(context, Variables.ACTIVE_DIALOG_SEQUENCE_ID, 6)
            bot.managers.storage.set(context, Variables.ACTIVE_DIALOG_SEQUENCE_ITEM_INDEX, 0)
            await _finalize_and_show_summary(bot, update, context, dialog, data)
            return CallbackResult.continue_()
        return CallbackResult.continue_()

    # --- Телефон арендатора ---
    if item_id == 105:
        if not is_valid_belarus_phone(answer or ""):
            set_dialog_position(bot, context, sequence_id, _idx())
            await bot.send_message(
                update, context, "guest_parking_tenant_phone_error", dynamic=False
            )
            return CallbackResult.retry_current(sequence_id, _idx())
        data["tenant_phone"] = _normalize_phone(answer or "")
        bot.managers.storage.set(context, Variables.GUEST_PARKING_DATA, data)
        user_id = bot.get_user_id(update)
        user = await bot.services.user.get_user_by_id(user_id) if user_id else None
        if user and (not user.phone_number or not user.phone_number.strip()):
            await bot.services.user.update_user(user_id, {"phone_number": data["tenant_phone"]})
            await bot.send_message(
                update, context, "profile_phone_saved", dynamic=False
            )
        bot.managers.storage.set(context, Variables.ACTIVE_DIALOG_SEQUENCE_ID, 6)
        bot.managers.storage.set(context, Variables.ACTIVE_DIALOG_SEQUENCE_ITEM_INDEX, 0)
        await _finalize_and_show_summary(bot, update, context, dialog, data)
        return CallbackResult.continue_()

    if state == 1:
        bot.managers.storage.set(context, Variables.GUEST_PARKING_DATA, None)
        return await bot.managers.navigator.execute(Dialogs.MENU, update, context)

    return CallbackResult.continue_()


async def _finalize_and_show_summary(
    bot: "Bot",
    update: "Update",
    context: "ContextTypes.DEFAULT_TYPE",
    dialog: "Dialog",
    data: dict,
) -> None:
    """Создаёт заявку, уведомляет админов, планирует напоминание, формирует финальный текст."""
    user_id = bot.get_user_id(update)
    if not user_id:
        return

    arrival_date = data.get("arrival_date")
    arrival_time = data.get("arrival_time", "")
    if isinstance(arrival_date, datetime):
        parts = arrival_time.split(":")
        hour = int(parts[0]) if parts else 9
        minute = int(parts[1]) if len(parts) > 1 else 0
        arrival_dt = arrival_date.replace(
            hour=hour,
            minute=minute,
            second=0,
            microsecond=0,
        )
    else:
        arrival_dt = now()

    # TIMESTAMPTZ: naive → Europe/Minsk
    from shared.utils.time_utils import SYSTEM_TIMEZONE
    arrival_dt_save = arrival_dt if arrival_dt.tzinfo else arrival_dt.replace(tzinfo=SYSTEM_TIMEZONE)

    from shared.schemas import GuestParkingSchema
    result = await bot.managers.database.guest_parking.create(
        model_data={
            "user_id": user_id,
            "arrival_date": arrival_dt_save.isoformat(),
            "license_plate": data.get("license_plate", ""),
            "car_make_color": data.get("car_make_color", ""),
            "driver_phone": data.get("driver_phone", ""),
            "tenant_phone": data.get("tenant_phone"),
        },
        model_class=GuestParkingSchema,
    )
    if not result.get("success"):
        await bot.send_message(
            update, context, "guest_parking_save_error", dynamic=False
        )
        return

    saved = result.get("data")
    req_id = saved.id if saved else None

    await bot.services.notification.notify_guest_parking_request(
        req_id=req_id,
        data=data,
        user_id=user_id,
    )
    await bot.services.notification.schedule_guest_parking_reminder(
        req_id=req_id,
        data=data,
    )

    # Формируем итоговый текст для финального экрана
    date_str = arrival_dt.strftime("%d.%m.%Y") if arrival_date else ""
    time_str = data.get("arrival_time", "")
    summary = bot.get_text(
        "guest_parking_final_summary",
        [
            date_str,
            time_str,
            data.get("license_plate", ""),
            data.get("car_make_color", ""),
            data.get("driver_phone", ""),
        ],
    )
    final_item = dialog.items.get(106)
    if final_item:
        final_item.text = summary
        # Заглушки для скриншотов — заменить на реальные URL
        final_item.images = []  # TODO: добавить URL скриншотов по схеме проезда
