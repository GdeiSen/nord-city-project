#!/usr/bin/env python3
"""
Миграция: рефакторинг аудита и вынесение Telegram message refs.

Что делает:
  1. Создает таблицу bot_message_refs
  2. Обновляет таблицу audit_log до новой структуры

Использование:
    python infrastructure/scripts/migrate_audit_refactor.py
"""

import os
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

_SCRIPT_DIR = Path(__file__).resolve().parent
INFRASTRUCTURE_ROOT = _SCRIPT_DIR.parent
if str(INFRASTRUCTURE_ROOT) not in sys.path:
    sys.path.insert(0, str(INFRASTRUCTURE_ROOT))
PROJECT_ROOT = INFRASTRUCTURE_ROOT.parent

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
    sys.exit(1)

db_src = INFRASTRUCTURE_ROOT / "services" / "database_service" / "src"
if str(db_src) not in sys.path:
    sys.path.insert(0, str(db_src))

from models.audit_log import AuditLog
from models.bot_message_ref import BotMessageRef


def get_db_url() -> str:
    host = os.getenv("DB_HOST", "127.0.0.1")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME", "nordcity_db")
    user = os.getenv("DB_USER", "nordcity_app")
    password = os.getenv("DB_PASSWORD", "")
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{name}"


AUDIT_TRIGGER_DROP_USER_TRIGGERS_SQL = """
DO $$
DECLARE
    trigger_rec record;
BEGIN
    FOR trigger_rec IN
        SELECT tg.tgname
        FROM pg_trigger tg
        JOIN pg_class cls ON cls.oid = tg.tgrelid
        JOIN pg_namespace ns ON ns.oid = cls.relnamespace
        WHERE cls.relname = 'audit_log'
          AND ns.nspname = current_schema()
          AND NOT tg.tgisinternal
    LOOP
        EXECUTE format('DROP TRIGGER IF EXISTS %I ON %I.%I', trigger_rec.tgname, current_schema(), 'audit_log');
    END LOOP;
END $$;
"""

AUDIT_TRIGGER_CREATE_FUNCTION_SQL = """
CREATE OR REPLACE FUNCTION audit_log_fill_defaults_trigger()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.event_type := COALESCE(NULLIF(NEW.event_type, ''), 'ENTITY_CHANGE');
    NEW.source_service := COALESCE(NULLIF(NEW.source_service, ''), 'database_service');
    NEW.retention_class := COALESCE(NULLIF(NEW.retention_class, ''), 'OPERATIONAL');

    IF NEW.actor_type IS NULL OR NEW.actor_type = '' THEN
        NEW.actor_type := CASE
            WHEN NEW.actor_id IS NOT NULL AND NEW.actor_id > 1 THEN 'USER'
            WHEN COALESCE(NEW.source_service, 'database_service') NOT IN ('database_service', 'web_service') THEN 'SERVICE'
            ELSE 'SYSTEM'
        END;
    END IF;

    IF NEW.meta IS NULL THEN
        NEW.meta := '{}'::json;
    END IF;

    RETURN NEW;
END;
$$;
"""

AUDIT_TRIGGER_DROP_SQL = "DROP TRIGGER IF EXISTS trg_audit_log_fill_defaults ON audit_log"

AUDIT_TRIGGER_CREATE_SQL = """
CREATE TRIGGER trg_audit_log_fill_defaults
BEFORE INSERT ON audit_log
FOR EACH ROW
EXECUTE FUNCTION audit_log_fill_defaults_trigger();
"""


async def ensure_bot_message_refs(engine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(lambda c: BotMessageRef.__table__.create(c, checkfirst=True))
        await conn.execute(text("CREATE SEQUENCE IF NOT EXISTS bot_message_refs_id_seq"))
        await conn.execute(
            text(
                """
                ALTER TABLE bot_message_refs
                ALTER COLUMN id
                SET DEFAULT nextval('bot_message_refs_id_seq'::regclass)
                """
            )
        )
        await conn.execute(
            text(
                """
                SELECT setval(
                    'bot_message_refs_id_seq',
                    COALESCE((SELECT MAX(id) FROM bot_message_refs), 1),
                    EXISTS (SELECT 1 FROM bot_message_refs)
                )
                """
            )
        )
    print("  [OK] Таблица bot_message_refs создана или уже существует")


async def migrate_audit_log(engine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(lambda c: AuditLog.__table__.create(c, checkfirst=True))
        await conn.execute(
            text(
                """
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1
                        FROM information_schema.columns
                        WHERE table_name = 'audit_log' AND column_name = 'assignee_id'
                    ) AND NOT EXISTS (
                        SELECT 1
                        FROM information_schema.columns
                        WHERE table_name = 'audit_log' AND column_name = 'actor_id'
                    ) THEN
                        ALTER TABLE audit_log RENAME COLUMN assignee_id TO actor_id;
                    END IF;
                END $$;
                """
            )
        )
        await conn.execute(text("ALTER TABLE audit_log ALTER COLUMN entity_id TYPE BIGINT"))
        await conn.execute(
            text("ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS event_type VARCHAR(64) DEFAULT 'ENTITY_CHANGE'")
        )
        await conn.execute(
            text("ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS actor_type VARCHAR(16) DEFAULT 'SYSTEM'")
        )
        await conn.execute(
            text("ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS source_service VARCHAR(64) DEFAULT 'database_service'")
        )
        await conn.execute(
            text("ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS retention_class VARCHAR(16) DEFAULT 'OPERATIONAL'")
        )
        await conn.execute(
            text("ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS request_id VARCHAR(128)")
        )
        await conn.execute(
            text("ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS correlation_id VARCHAR(128)")
        )
        await conn.execute(
            text("ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS reason VARCHAR(255)")
        )

        await conn.execute(text("UPDATE audit_log SET event_type = COALESCE(event_type, 'ENTITY_CHANGE')"))
        await conn.execute(
            text(
                """
                UPDATE audit_log
                SET source_service = COALESCE(
                    NULLIF(source_service, ''),
                    NULLIF(meta::jsonb ->> 'source', ''),
                    'database_service'
                )
                """
            )
        )
        await conn.execute(
            text(
                """
                UPDATE audit_log
                SET actor_type = CASE
                    WHEN actor_id IS NOT NULL AND actor_id > 1 THEN 'USER'
                    WHEN COALESCE(source_service, 'database_service') NOT IN ('database_service', 'web_service') THEN 'SERVICE'
                    ELSE 'SYSTEM'
                END
                WHERE actor_type IS NULL OR actor_type = ''
                """
            )
        )
        await conn.execute(
            text(
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
            )
        )
        await conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_audit_log_created ON audit_log (created_at)"
            )
        )
        await conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_audit_log_actor_created ON audit_log (actor_id, created_at)"
            )
        )
        await conn.execute(text(AUDIT_TRIGGER_DROP_USER_TRIGGERS_SQL))
        await conn.execute(text(AUDIT_TRIGGER_CREATE_FUNCTION_SQL))
        await conn.execute(text(AUDIT_TRIGGER_DROP_SQL))
        await conn.execute(text(AUDIT_TRIGGER_CREATE_SQL))
    print("  [OK] Таблица audit_log обновлена до новой структуры")


async def run_migration():
    engine = create_async_engine(get_db_url(), echo=False)
    try:
        print("\n=== Миграция аудита ===\n")
        print("Шаг 1/2: Создание таблицы bot_message_refs...")
        await ensure_bot_message_refs(engine)
        print("\nШаг 2/2: Обновление таблицы audit_log...")
        await migrate_audit_log(engine)
        print("\n=== Миграция успешно завершена ===\n")
    finally:
        await engine.dispose()


def main():
    import asyncio

    try:
        asyncio.run(run_migration())
    except Exception as e:
        print(f"Ошибка миграции: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
