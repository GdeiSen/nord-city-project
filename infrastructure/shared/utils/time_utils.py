from datetime import datetime, timezone, timedelta

# Часовой пояс системы — Минск (UTC+3)
SYSTEM_TIMEZONE = timezone(timedelta(hours=3))


def now() -> datetime:
    """Текущее время в системном часовом поясе (Минск)."""
    return datetime.now(SYSTEM_TIMEZONE)


def to_system_time(dt: datetime) -> datetime:
    """Конвертирует datetime в системный часовой пояс. Naive считаем UTC."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(SYSTEM_TIMEZONE)
