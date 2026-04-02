#!/usr/bin/env python3
"""
Миграция: поддержка объектной маршрутизации Telegram-чатов.

Что делает:
  1. Создаёт таблицу telegram_chats
  2. Добавляет objects.admin_chat_id
  3. Добавляет guest_parking_requests.object_id
  4. Переносит chat_id из существующих bot_message_refs в telegram_chats
  5. Связывает bot_message_refs.chat_id с telegram_chats.chat_id
  6. Заполняет service_tickets.object_id из users.object_id, где это возможно
  7. Заполняет guest_parking_requests.object_id из users.object_id, где это возможно
  8. Добавляет legacy ADMIN_CHAT_ID в telegram_chats как fallback-чат, если он задан

Использование:
    python infrastructure/scripts/add_chat_routing_support.py
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

from models.telegram_chat import TelegramChat


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
            await conn.run_sync(lambda c: TelegramChat.__table__.create(c, checkfirst=True))

            await conn.execute(
                text(
                    """
                    ALTER TABLE objects
                    ADD COLUMN IF NOT EXISTS admin_chat_id BIGINT
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    ALTER TABLE guest_parking_requests
                    ADD COLUMN IF NOT EXISTS object_id INTEGER
                    """
                )
            )

            await conn.execute(
                text(
                    """
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1
                            FROM information_schema.table_constraints
                            WHERE table_name = 'objects'
                              AND constraint_name = 'fk_objects_admin_chat_id_telegram_chats'
                        ) THEN
                            ALTER TABLE objects
                            ADD CONSTRAINT fk_objects_admin_chat_id_telegram_chats
                            FOREIGN KEY (admin_chat_id) REFERENCES telegram_chats(chat_id)
                            ON DELETE SET NULL;
                        END IF;
                    END $$;
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1
                            FROM information_schema.table_constraints
                            WHERE table_name = 'guest_parking_requests'
                              AND constraint_name = 'fk_guest_parking_requests_object_id_objects'
                        ) THEN
                            ALTER TABLE guest_parking_requests
                            ADD CONSTRAINT fk_guest_parking_requests_object_id_objects
                            FOREIGN KEY (object_id) REFERENCES objects(id)
                            ON DELETE SET NULL;
                        END IF;
                    END $$;
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    DO $$
                    BEGIN
                        IF EXISTS (
                            SELECT 1
                            FROM information_schema.tables
                            WHERE table_name = 'bot_message_refs'
                        ) THEN
                            INSERT INTO telegram_chats (
                                chat_id,
                                title,
                                chat_type,
                                is_active,
                                bot_status,
                                last_seen_at,
                                meta
                            )
                            SELECT DISTINCT
                                bmr.chat_id,
                                CONCAT('Imported chat ', bmr.chat_id::text),
                                'group',
                                TRUE,
                                'imported_from_refs',
                                NOW(),
                                json_build_object('source', 'bot_message_refs_backfill')
                            FROM bot_message_refs bmr
                            LEFT JOIN telegram_chats tc ON tc.chat_id = bmr.chat_id
                            WHERE tc.chat_id IS NULL;
                        END IF;
                    END $$;
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    DO $$
                    BEGIN
                        IF EXISTS (
                            SELECT 1
                            FROM information_schema.tables
                            WHERE table_name = 'bot_message_refs'
                        ) AND NOT EXISTS (
                            SELECT 1
                            FROM information_schema.table_constraints
                            WHERE table_name = 'bot_message_refs'
                              AND constraint_name = 'fk_bot_message_refs_chat_id_telegram_chats'
                        ) THEN
                            ALTER TABLE bot_message_refs
                            ADD CONSTRAINT fk_bot_message_refs_chat_id_telegram_chats
                            FOREIGN KEY (chat_id) REFERENCES telegram_chats(chat_id);
                        END IF;
                    END $$;
                    """
                )
            )

            await conn.execute(
                text(
                    """
                    UPDATE service_tickets st
                    SET object_id = u.object_id
                    FROM users u
                    WHERE st.user_id = u.id
                      AND st.object_id IS NULL
                      AND u.object_id IS NOT NULL
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    UPDATE guest_parking_requests gpr
                    SET object_id = u.object_id
                    FROM users u
                    WHERE gpr.user_id = u.id
                      AND gpr.object_id IS NULL
                      AND u.object_id IS NOT NULL
                    """
                )
            )

            legacy_admin_chat_id = os.getenv("ADMIN_CHAT_ID", "").strip()
            if legacy_admin_chat_id:
                try:
                    legacy_chat_id = int(legacy_admin_chat_id)
                except (TypeError, ValueError):
                    raise RuntimeError("ADMIN_CHAT_ID должен быть целым числом")

                await conn.execute(
                    text(
                        """
                        INSERT INTO telegram_chats (
                            chat_id,
                            title,
                            chat_type,
                            is_active,
                            bot_status,
                            last_seen_at,
                            meta
                        )
                        VALUES (
                            :chat_id,
                            :title,
                            'group',
                            TRUE,
                            'legacy_fallback',
                            NOW(),
                            json_build_object('source', 'chat_routing_migration')
                        )
                        ON CONFLICT (chat_id) DO UPDATE
                        SET
                            title = EXCLUDED.title,
                            is_active = TRUE,
                            bot_status = EXCLUDED.bot_status,
                            last_seen_at = NOW(),
                            meta = COALESCE(telegram_chats.meta, '{}'::json) || EXCLUDED.meta
                        """
                    ),
                    {
                        "chat_id": legacy_chat_id,
                        "title": "Legacy admin chat",
                    },
                )

        print("Таблица telegram_chats создана или уже существует.")
        print("Колонки objects.admin_chat_id и guest_parking_requests.object_id готовы.")
        print("Связь bot_message_refs.chat_id -> telegram_chats.chat_id подготовлена.")
        print("Backfill service_tickets.object_id и guest_parking_requests.object_id выполнен.")
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
