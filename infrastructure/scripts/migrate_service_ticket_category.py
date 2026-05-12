#!/usr/bin/env python3
"""Adds category support for service tickets."""

import logging
import os
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

_SCRIPT_DIR = Path(__file__).resolve().parent
INFRASTRUCTURE_ROOT = _SCRIPT_DIR.parent
PROJECT_ROOT = INFRASTRUCTURE_ROOT.parent
if str(INFRASTRUCTURE_ROOT) not in sys.path:
    sys.path.insert(0, str(INFRASTRUCTURE_ROOT))

env_path = PROJECT_ROOT / ".env"
if env_path.exists():
    try:
        from dotenv import load_dotenv

        load_dotenv(dotenv_path=env_path, override=False)
    except ImportError:
        pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def get_db_url() -> str:
    host = os.getenv("DB_HOST", "127.0.0.1")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME", "nordcity_db")
    user = os.getenv("DB_USER", "nordcity_app")
    password = os.getenv("DB_PASSWORD", "")
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{name}"


async def main() -> None:
    missing = [name for name in ("DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD") if not os.getenv(name)]
    if missing:
        raise RuntimeError(f"Не заданы переменные окружения: {', '.join(missing)}")

    engine = create_async_engine(get_db_url(), echo=False)
    async with engine.begin() as conn:
        await conn.execute(text("ALTER TABLE service_tickets ADD COLUMN IF NOT EXISTS category VARCHAR(200)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_service_tickets_category ON service_tickets (category)"))
    await engine.dispose()
    logger.info("Service ticket category migration completed.")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
