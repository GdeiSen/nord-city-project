#!/usr/bin/env python3
"""
Миграция: удаление колонки reminder_sent из guest_parking_requests.
Оповещения теперь работают только по времени прибытия без сохранения состояния.
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


async def run_migration():
    url = get_db_url()
    engine = create_async_engine(url, echo=False)

    async with engine.begin() as conn:
        await conn.execute(text(
            "ALTER TABLE guest_parking_requests DROP COLUMN IF EXISTS reminder_sent"
        ))
        print("Колонка reminder_sent удалена (или отсутствовала).")

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
