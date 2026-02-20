#!/usr/bin/env python3
"""
Объединённый скрипт миграции: переход со старой версии Nord City на новую.

Выполняет по порядку:
  1. Создание таблицы guest_parking_requests (если не существует)
  2. Миграция колонок TIMESTAMP → TIMESTAMPTZ
  3. Добавление колонки msid в guest_parking_requests
  4. Удаление колонки reminder_sent из guest_parking_requests

Использование:
    Из корня проекта:
        python infrastructure/scripts/migrate_all.py

    Требуется .env с DB_HOST, DB_NAME, DB_USER, DB_PASSWORD.
"""
import os
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
INFRASTRUCTURE_ROOT = _SCRIPT_DIR.parent
if str(INFRASTRUCTURE_ROOT) not in sys.path:
    sys.path.insert(0, str(INFRASTRUCTURE_ROOT))
PROJECT_ROOT = INFRASTRUCTURE_ROOT.parent

# Загрузка .env
env_path = PROJECT_ROOT / ".env"
if env_path.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=env_path, override=False)
    except ImportError:
        pass

required = ["DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD"]
missing = [v for v in required if not os.getenv(v)]
if missing:
    print(f"Ошибка: не заданы переменные окружения: {', '.join(missing)}")
    print(f"Убедитесь, что .env существует в {PROJECT_ROOT}")
    sys.exit(1)

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

db_src = INFRASTRUCTURE_ROOT / "services" / "database_service" / "src"
if str(db_src) not in sys.path:
    sys.path.insert(0, str(db_src))
from models.guest_parking_request import GuestParkingRequest


def get_db_url() -> str:
    host = os.getenv("DB_HOST", "127.0.0.1")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME", "nordcity_db")
    user = os.getenv("DB_USER", "nordcity_app")
    password = os.getenv("DB_PASSWORD", "")
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{name}"


# (table, column) — все DateTime-колонки для миграции в timestamptz
TIMESTAMPTZ_COLUMNS = [
    ("guest_parking_requests", "arrival_date"),
    ("guest_parking_requests", "created_at"),
    ("guest_parking_requests", "updated_at"),
    ("audit_log", "created_at"),
    ("object_space_views", "created_at"),
    ("object_space_views", "updated_at"),
    ("otp_codes", "expires_at"),
    ("otp_codes", "created_at"),
    ("object_spaces", "created_at"),
    ("object_spaces", "updated_at"),
    ("feedbacks", "created_at"),
    ("feedbacks", "updated_at"),
    ("poll_answers", "created_at"),
    ("poll_answers", "updated_at"),
    ("users", "created_at"),
    ("users", "updated_at"),
    ("service_tickets", "created_at"),
    ("service_tickets", "updated_at"),
    ("objects", "created_at"),
    ("objects", "updated_at"),
    ("user_auth", "created_at"),
    ("user_auth", "updated_at"),
]


async def step1_create_guest_parking(engine):
    """Создание таблицы guest_parking_requests."""
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda c: GuestParkingRequest.__table__.create(c, checkfirst=True)
        )
    print("  [OK] Таблица guest_parking_requests создана или уже существует")


async def step2_migrate_timestamptz(engine):
    """Миграция TIMESTAMP → TIMESTAMPTZ (существующие значения как UTC)."""
    failed = []
    for table, column in TIMESTAMPTZ_COLUMNS:
        try:
            async with engine.begin() as conn:
                await conn.execute(text(f"""
                    ALTER TABLE {table}
                    ALTER COLUMN {column} TYPE TIMESTAMP WITH TIME ZONE
                    USING {column} AT TIME ZONE 'UTC'
                """))
            print(f"  [OK] {table}.{column} → timestamptz")
        except Exception as e:
            msg = str(e).split("\n")[0]
            print(f"  [SKIP] {table}.{column}: {msg}")
            failed.append((table, column, str(e)))
    if failed:
        print(f"\n  Пропущено {len(failed)} колонок (таблица/колонка отсутствует или уже timestamptz)")
    print("  [OK] Миграция TIMESTAMPTZ завершена")


async def step3_add_msid(engine):
    """Добавление колонки msid в guest_parking_requests."""
    async with engine.begin() as conn:
        await conn.execute(text(
            "ALTER TABLE guest_parking_requests ADD COLUMN IF NOT EXISTS msid BIGINT"
        ))
    print("  [OK] Колонка msid добавлена или уже существует")


async def step4_drop_reminder_sent(engine):
    """Удаление колонки reminder_sent из guest_parking_requests."""
    async with engine.begin() as conn:
        await conn.execute(text(
            "ALTER TABLE guest_parking_requests DROP COLUMN IF EXISTS reminder_sent"
        ))
    print("  [OK] Колонка reminder_sent удалена или отсутствовала")


async def run_all():
    url = get_db_url()
    engine = create_async_engine(url, echo=False)

    print("\n=== Миграция Nord City: старая → новая версия ===\n")

    print("Шаг 1/4: Создание таблицы guest_parking_requests...")
    await step1_create_guest_parking(engine)

    print("\nШаг 2/4: Миграция TIMESTAMP → TIMESTAMPTZ...")
    await step2_migrate_timestamptz(engine)

    print("\nШаг 3/4: Добавление колонки msid...")
    await step3_add_msid(engine)

    print("\nШаг 4/4: Удаление колонки reminder_sent...")
    await step4_drop_reminder_sent(engine)

    await engine.dispose()
    print("\n=== Миграция успешно завершена ===\n")


def main():
    import asyncio
    try:
        asyncio.run(run_all())
    except Exception as e:
        print(f"\nОшибка миграции: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
