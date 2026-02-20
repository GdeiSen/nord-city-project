#!/usr/bin/env python3
"""
Миграция: TIMESTAMP WITHOUT TIME ZONE → TIMESTAMP WITH TIME ZONE.

Существующие naive-значения интерпретируются как UTC.
После миграции asyncpg корректно работает с timezone-aware datetime.
"""
import os
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
INFRASTRUCTURE_ROOT = _SCRIPT_DIR.parent
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
    print(f"Ошибка: не заданы переменные: {', '.join(missing)}")
    sys.exit(1)

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


def get_db_url() -> str:
    host = os.getenv("DB_HOST", "127.0.0.1")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME", "nordcity_db")
    user = os.getenv("DB_USER", "nordcity_app")
    password = os.getenv("DB_PASSWORD", "")
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{name}"


# (table, column) — все DateTime-колонки в проекте
COLUMNS = [
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


async def run_migration():
    url = get_db_url()
    engine = create_async_engine(url, echo=False)

    async with engine.begin() as conn:
        for table, column in COLUMNS:
            try:
                await conn.execute(text(f"""
                    ALTER TABLE {table}
                    ALTER COLUMN {column} TYPE TIMESTAMP WITH TIME ZONE
                    USING {column} AT TIME ZONE 'UTC'
                """))
                print(f"  {table}.{column} → timestamptz")
            except Exception as e:
                print(f"  {table}.{column}: {e}")
                raise

    await engine.dispose()
    print("Миграция TIMESTAMPTZ завершена.")


def main():
    import asyncio
    try:
        asyncio.run(run_migration())
    except Exception as e:
        print(f"Ошибка миграции: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
