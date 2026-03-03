#!/usr/bin/env python3
"""
Миграция: перенос legacy service_tickets.msid в bot_message_refs и удаление колонки.

Что делает:
  1. Создаёт таблицу bot_message_refs, если её ещё нет
  2. Переносит service_tickets.msid в bot_message_refs(kind=PRIMARY)
  3. Удаляет колонку msid из service_tickets

Использование:
    python infrastructure/scripts/drop_service_ticket_msid.py

Требования:
    Если есть тикеты с ненулевым msid без PRIMARY-ссылки в bot_message_refs,
    в окружении должна быть задана переменная ADMIN_CHAT_ID.
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

from models.bot_message_ref import BotMessageRef


def get_db_url() -> str:
    host = os.getenv("DB_HOST", "127.0.0.1")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME", "nordcity_db")
    user = os.getenv("DB_USER", "nordcity_app")
    password = os.getenv("DB_PASSWORD", "")
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{name}"


async def run_migration():
    engine = create_async_engine(get_db_url(), echo=False)
    try:
        async with engine.begin() as conn:
            column_exists = await conn.scalar(
                text(
                    """
                    SELECT EXISTS (
                        SELECT 1
                        FROM information_schema.columns
                        WHERE table_name = 'service_tickets' AND column_name = 'msid'
                    )
                    """
                )
            )
            if not column_exists:
                print("Колонка service_tickets.msid уже отсутствует.")
                return

            await conn.run_sync(lambda c: BotMessageRef.__table__.create(c, checkfirst=True))

            pending_backfill = await conn.scalar(
                text(
                    """
                    SELECT COUNT(*)
                    FROM service_tickets st
                    WHERE st.msid IS NOT NULL
                      AND NOT EXISTS (
                          SELECT 1
                          FROM bot_message_refs bmr
                          WHERE bmr.entity_type = 'ServiceTicket'
                            AND bmr.entity_id = st.id
                            AND bmr.kind = 'PRIMARY'
                      )
                    """
                )
            )
            pending_backfill = int(pending_backfill or 0)

            inserted = 0
            if pending_backfill > 0:
                admin_chat_id_raw = os.getenv("ADMIN_CHAT_ID")
                if not admin_chat_id_raw:
                    raise RuntimeError(
                        "Найдены legacy service_tickets.msid без bot_message_refs, "
                        "но переменная ADMIN_CHAT_ID не задана. "
                        "Укажите ADMIN_CHAT_ID и повторите миграцию."
                    )
                try:
                    admin_chat_id = int(str(admin_chat_id_raw).strip())
                except (TypeError, ValueError) as exc:
                    raise RuntimeError("ADMIN_CHAT_ID должен быть целым числом") from exc

                result = await conn.execute(
                    text(
                        """
                        INSERT INTO bot_message_refs (
                            entity_type,
                            entity_id,
                            chat_id,
                            message_id,
                            kind,
                            meta
                        )
                        SELECT
                            'ServiceTicket',
                            st.id,
                            :admin_chat_id,
                            st.msid,
                            'PRIMARY',
                            json_build_object('source', 'service_ticket_msid_migration')
                        FROM service_tickets st
                        WHERE st.msid IS NOT NULL
                          AND NOT EXISTS (
                              SELECT 1
                              FROM bot_message_refs bmr
                              WHERE bmr.entity_type = 'ServiceTicket'
                                AND bmr.entity_id = st.id
                                AND bmr.kind = 'PRIMARY'
                          )
                        ON CONFLICT (chat_id, message_id) DO NOTHING
                        """
                    ),
                    {"admin_chat_id": admin_chat_id},
                )
                inserted = result.rowcount or 0

            await conn.execute(
                text("ALTER TABLE service_tickets DROP COLUMN IF EXISTS msid")
            )

            if pending_backfill > 0:
                print(f"Перенесено PRIMARY message refs: {inserted}")
            print("Колонка service_tickets.msid удалена или отсутствовала.")
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
