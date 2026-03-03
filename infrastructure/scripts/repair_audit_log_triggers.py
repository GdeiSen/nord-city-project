#!/usr/bin/env python3
"""
Hotfix: пересоздание пользовательских trigger-ов audit_log после перехода
с assignee_id на actor_id.

Что делает:
  1. Удаляет все пользовательские trigger-ы на таблице audit_log
  2. Создает новую trigger-функцию audit_log_fill_defaults_trigger()
  3. Создает trigger trg_audit_log_fill_defaults

Использование:
    python infrastructure/scripts/repair_audit_log_triggers.py
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


def get_db_url() -> str:
    host = os.getenv("DB_HOST", "127.0.0.1")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME", "nordcity_db")
    user = os.getenv("DB_USER", "nordcity_app")
    password = os.getenv("DB_PASSWORD", "")
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{name}"


REBUILD_SQL = """
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

DROP TRIGGER IF EXISTS trg_audit_log_fill_defaults ON audit_log;

CREATE TRIGGER trg_audit_log_fill_defaults
BEFORE INSERT ON audit_log
FOR EACH ROW
EXECUTE FUNCTION audit_log_fill_defaults_trigger();
"""


async def run_migration():
    engine = create_async_engine(get_db_url(), echo=False)
    try:
        async with engine.begin() as conn:
            await conn.execute(text(REBUILD_SQL))
        print("Пользовательские trigger-ы audit_log пересозданы под actor_id.")
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
