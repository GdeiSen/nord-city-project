#!/usr/bin/env python3
"""
Скрипт миграции: создание таблицы guest_parking_requests.

Загружает переменные из .env в корне проекта и создаёт таблицу,
если её ещё нет.

Использование:
    cd infrastructure/services/database_service/src
    python ../../../../scripts/migrate_guest_parking.py

или из корня проекта (с PYTHONPATH):
    PYTHONPATH=infrastructure python infrastructure/scripts/migrate_guest_parking.py
"""
import os
import sys
from pathlib import Path

# infrastructure/ — для импорта shared
_SCRIPT_DIR = Path(__file__).resolve().parent
INFRASTRUCTURE_ROOT = _SCRIPT_DIR.parent
if str(INFRASTRUCTURE_ROOT) not in sys.path:
    sys.path.insert(0, str(INFRASTRUCTURE_ROOT))
PROJECT_ROOT = INFRASTRUCTURE_ROOT.parent

# Загружаем .env из корня проекта (опционально)
env_path = PROJECT_ROOT / ".env"
if env_path.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=env_path, override=False)
    except ImportError:
        pass  # dotenv не установлен — используем переменные из окружения

# Проверяем переменные ДО импорта конфига (который их читает)
required = ["DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD"]
missing = [v for v in required if not os.getenv(v)]
if missing:
    print(f"Ошибка: не заданы переменные окружения: {', '.join(missing)}")
    print(f"Убедитесь, что файл .env существует в {PROJECT_ROOT}")
    sys.exit(1)

# Импорты после загрузки .env
from sqlalchemy.ext.asyncio import create_async_engine

# ORM теперь в database_service
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


async def run_migration():
    url = get_db_url()
    engine = create_async_engine(url, echo=False)

    async with engine.begin() as conn:
        # Создаём таблицу, если её ещё нет (checkfirst=True)
        await conn.run_sync(
            lambda c: GuestParkingRequest.__table__.create(c, checkfirst=True)
        )
        print("Таблица guest_parking_requests успешно создана (или уже существует).")

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
