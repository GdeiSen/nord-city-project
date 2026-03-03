#!/usr/bin/env python3
"""
Объединённый скрипт миграции: переход со старой версии Nord City на новую.

Выполняет по порядку:
  1. Создание таблицы guest_parking_requests (если не существует)
  2. Миграция колонок TIMESTAMP → TIMESTAMPTZ
  3. Добавление колонки msid в guest_parking_requests
  4. Удаление колонки reminder_sent из guest_parking_requests
  5. Удаление колонки reminder_sent_at из guest_parking_requests
  6. Удаление колонки driver_phone из guest_parking_requests
  7. Создание таблицы guest_parking_settings
  8. Создание таблицы storage_files
  9. Рефакторинг аудита (новые поля audit_log + bot_message_refs)

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
from models.guest_parking_settings import GuestParkingSettings
from models.audit_log import AuditLog
from models.storage_file import StorageFile
from models.bot_message_ref import BotMessageRef


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


async def step5_drop_reminder_sent_at(engine):
    """Удаление колонки reminder_sent_at — учёт напоминаний перенесён в in-memory кэш database_service."""
    async with engine.begin() as conn:
        await conn.execute(text(
            "ALTER TABLE guest_parking_requests DROP COLUMN IF EXISTS reminder_sent_at"
        ))
    print("  [OK] Колонка reminder_sent_at удалена или отсутствовала")


async def step6_drop_driver_phone(engine):
    """Удаление колонки driver_phone из guest_parking_requests."""
    async with engine.begin() as conn:
        await conn.execute(text(
            "ALTER TABLE guest_parking_requests DROP COLUMN IF EXISTS driver_phone"
        ))
    print("  [OK] Колонка driver_phone удалена или отсутствовала")


async def step7_create_guest_parking_settings(engine):
    """Создание таблицы guest_parking_settings."""
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda c: GuestParkingSettings.__table__.create(c, checkfirst=True)
        )
    print("  [OK] Таблица guest_parking_settings создана или уже существует")


async def step8_create_storage_files(engine):
    """Создание таблицы storage_files."""
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda c: StorageFile.__table__.create(c, checkfirst=True)
        )
    print("  [OK] Таблица storage_files создана или уже существует")


async def step9_migrate_audit(engine):
    """Рефакторинг audit_log и создание bot_message_refs."""
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda c: AuditLog.__table__.create(c, checkfirst=True)
        )
        await conn.run_sync(
            lambda c: BotMessageRef.__table__.create(c, checkfirst=True)
        )
        await conn.execute(text(
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'audit_log' AND column_name = 'assignee_id'
                ) AND NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'audit_log' AND column_name = 'actor_id'
                ) THEN
                    ALTER TABLE audit_log RENAME COLUMN assignee_id TO actor_id;
                END IF;
            END $$;
            """
        ))
        await conn.execute(text("ALTER TABLE audit_log ALTER COLUMN entity_id TYPE BIGINT"))
        await conn.execute(text("ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS event_type VARCHAR(64) DEFAULT 'ENTITY_CHANGE'"))
        await conn.execute(text("ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS actor_type VARCHAR(16) DEFAULT 'SYSTEM'"))
        await conn.execute(text("ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS source_service VARCHAR(64) DEFAULT 'database_service'"))
        await conn.execute(text("ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS retention_class VARCHAR(16) DEFAULT 'OPERATIONAL'"))
        await conn.execute(text("ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS request_id VARCHAR(128)"))
        await conn.execute(text("ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS correlation_id VARCHAR(128)"))
        await conn.execute(text("ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS reason VARCHAR(255)"))
        await conn.execute(text("UPDATE audit_log SET event_type = COALESCE(event_type, 'ENTITY_CHANGE')"))
        await conn.execute(text(
            """
            UPDATE audit_log
            SET source_service = COALESCE(
                NULLIF(source_service, ''),
                NULLIF(meta::jsonb ->> 'source', ''),
                'database_service'
            )
            """
        ))
        await conn.execute(text(
            """
            UPDATE audit_log
            SET actor_type = CASE
                WHEN actor_id IS NOT NULL AND actor_id > 1 THEN 'USER'
                WHEN COALESCE(source_service, 'database_service') NOT IN ('database_service', 'web_service') THEN 'SERVICE'
                ELSE 'SYSTEM'
            END
            WHERE actor_type IS NULL OR actor_type = ''
            """
        ))
        await conn.execute(text(
            """
            UPDATE audit_log
            SET retention_class = CASE entity_type
                WHEN 'User' THEN 'CRITICAL'
                WHEN 'Object' THEN 'CRITICAL'
                WHEN 'Space' THEN 'CRITICAL'
                WHEN 'GuestParkingSettings' THEN 'CRITICAL'
                WHEN 'SpaceView' THEN 'TECHNICAL'
                WHEN 'StorageFile' THEN 'TECHNICAL'
                ELSE 'OPERATIONAL'
            END
            WHERE retention_class IS NULL OR retention_class = ''
            """
        ))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_audit_log_created ON audit_log (created_at)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_audit_log_actor_created ON audit_log (actor_id, created_at)"))
    print("  [OK] audit_log обновлен, bot_message_refs создана")


async def run_all():
    url = get_db_url()
    engine = create_async_engine(url, echo=False)

    print("\n=== Миграция Nord City: старая → новая версия ===\n")

    print("Шаг 1/9: Создание таблицы guest_parking_requests...")
    await step1_create_guest_parking(engine)

    print("\nШаг 2/9: Миграция TIMESTAMP → TIMESTAMPTZ...")
    await step2_migrate_timestamptz(engine)

    print("\nШаг 3/9: Добавление колонки msid...")
    await step3_add_msid(engine)

    print("\nШаг 4/9: Удаление колонки reminder_sent...")
    await step4_drop_reminder_sent(engine)

    print("\nШаг 5/9: Удаление колонки reminder_sent_at (логика в кэше)...")
    await step5_drop_reminder_sent_at(engine)

    print("\nШаг 6/9: Удаление колонки driver_phone...")
    await step6_drop_driver_phone(engine)

    print("\nШаг 7/9: Создание таблицы guest_parking_settings...")
    await step7_create_guest_parking_settings(engine)

    print("\nШаг 8/9: Создание таблицы storage_files...")
    await step8_create_storage_files(engine)

    print("\nШаг 9/9: Рефакторинг аудита...")
    await step9_migrate_audit(engine)

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
