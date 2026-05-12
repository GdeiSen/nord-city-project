#!/usr/bin/env python3
"""
Adds interval/status workflow fields for guest parking requests.

Backfills:
  arrival_start_at = arrival_date
  arrival_end_at = arrival_date + 2 hours
  status = NEW
"""

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
        await conn.execute(text("ALTER TABLE guest_parking_requests ADD COLUMN IF NOT EXISTS arrival_start_at TIMESTAMPTZ"))
        await conn.execute(text("ALTER TABLE guest_parking_requests ADD COLUMN IF NOT EXISTS arrival_end_at TIMESTAMPTZ"))
        await conn.execute(text("ALTER TABLE guest_parking_requests ADD COLUMN IF NOT EXISTS status VARCHAR(20)"))
        await conn.execute(text("ALTER TABLE guest_parking_requests ADD COLUMN IF NOT EXISTS reviewed_by_user_id BIGINT"))
        await conn.execute(text("ALTER TABLE guest_parking_requests ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMPTZ"))
        await conn.execute(text("ALTER TABLE guest_parking_requests ADD COLUMN IF NOT EXISTS rejection_reason TEXT"))
        await conn.execute(
            text(
                """
                UPDATE guest_parking_requests
                SET arrival_start_at = COALESCE(arrival_start_at, arrival_date),
                    arrival_end_at = COALESCE(arrival_end_at, arrival_date + INTERVAL '2 hours'),
                    status = COALESCE(NULLIF(status, ''), 'NEW')
                """
            )
        )
        await conn.execute(text("ALTER TABLE guest_parking_requests ALTER COLUMN status SET DEFAULT 'NEW'"))
        await conn.execute(text("ALTER TABLE guest_parking_requests ALTER COLUMN status SET NOT NULL"))
        await conn.execute(text("ALTER TABLE guest_parking_requests ALTER COLUMN arrival_start_at SET NOT NULL"))
        await conn.execute(text("ALTER TABLE guest_parking_requests ALTER COLUMN arrival_end_at SET NOT NULL"))
        await conn.execute(
            text(
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.table_constraints
                        WHERE table_name = 'guest_parking_requests'
                          AND constraint_name = 'fk_guest_parking_reviewed_by_user_id_users'
                    ) THEN
                        ALTER TABLE guest_parking_requests
                        ADD CONSTRAINT fk_guest_parking_reviewed_by_user_id_users
                        FOREIGN KEY (reviewed_by_user_id) REFERENCES users(id)
                        ON DELETE SET NULL;
                    END IF;
                END $$;
                """
            )
        )
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_guest_parking_requests_status ON guest_parking_requests (status)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_guest_parking_requests_arrival_start_at ON guest_parking_requests (arrival_start_at)"))
    await engine.dispose()
    logger.info("Guest parking interval/status migration completed.")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
