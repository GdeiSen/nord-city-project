#!/usr/bin/env python3
"""
Миграция: создание реестра DDID и связывание сущностей с canonical DDID.

Что делает:
  1. Создаёт таблицу dynamic_dialog_bindings
  2. Нормализует ddid в feedbacks, poll_answers и service_tickets
  3. Backfill-ит реестр из существующих значений ddid
  4. Добавляет внешние ключи на dynamic_dialog_bindings.ddid

Использование:
    python infrastructure/scripts/add_dynamic_dialog_bindings.py
"""

import logging
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
    logger.error("Не заданы переменные окружения: %s", ", ".join(missing))
    sys.exit(1)

db_src = INFRASTRUCTURE_ROOT / "services" / "database_service" / "src"
if str(db_src) not in sys.path:
    sys.path.insert(0, str(db_src))

from models.dynamic_dialog_binding import DynamicDialogBinding
from shared.utils.ddid_utils import normalize_ddid, parse_ddid

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DDID_TABLES = ("feedbacks", "poll_answers", "service_tickets")
PLACEHOLDER_DDID = "0000-0000-0000"


def get_db_url() -> str:
    host = os.getenv("DB_HOST", "127.0.0.1")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME", "nordcity_db")
    user = os.getenv("DB_USER", "nordcity_app")
    password = os.getenv("DB_PASSWORD", "")
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{name}"


def _normalize_existing_ddid(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return PLACEHOLDER_DDID
    return normalize_ddid(raw)


async def _normalize_table_ddids(conn, table_name: str) -> int:
    result = await conn.execute(
        text(f"SELECT DISTINCT ddid FROM {table_name}")
    )
    changed = 0
    for row in result:
        raw_ddid = row[0]
        if raw_ddid is None:
            continue
        normalized = _normalize_existing_ddid(raw_ddid)
        if normalized == raw_ddid:
            continue
        await conn.execute(
            text(f"UPDATE {table_name} SET ddid = :normalized WHERE ddid = :raw_ddid"),
            {"normalized": normalized, "raw_ddid": raw_ddid},
        )
        changed += 1
    return changed


async def _backfill_registry(conn) -> int:
    result = await conn.execute(
        text(
            """
            SELECT ddid FROM feedbacks
            UNION
            SELECT ddid FROM poll_answers
            UNION
            SELECT ddid FROM service_tickets
            """
        )
    )
    inserted = 0
    for row in result:
        ddid = row[0]
        if ddid is None:
            continue
        normalized = _normalize_existing_ddid(ddid)
        dialog_id, sequence_id, item_id = parse_ddid(normalized)
        insert_result = await conn.execute(
            text(
                """
                INSERT INTO dynamic_dialog_bindings (id, ddid, dialog_id, sequence_id, item_id)
                VALUES (nextval('dynamic_dialog_bindings_id_seq'::regclass), :ddid, :dialog_id, :sequence_id, :item_id)
                ON CONFLICT (ddid) DO NOTHING
                """
            ),
            {
                "ddid": normalized,
                "dialog_id": dialog_id,
                "sequence_id": sequence_id,
                "item_id": item_id,
            },
        )
        inserted += insert_result.rowcount or 0
    return inserted


async def _ensure_fk(conn, *, table_name: str, constraint_name: str) -> None:
    await conn.execute(
        text(
            f"""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1
                    FROM pg_constraint
                    WHERE conname = '{constraint_name}'
                ) THEN
                    ALTER TABLE {table_name}
                    ADD CONSTRAINT {constraint_name}
                    FOREIGN KEY (ddid)
                    REFERENCES dynamic_dialog_bindings(ddid)
                    ON UPDATE RESTRICT
                    ON DELETE RESTRICT;
                END IF;
            END $$;
            """
        )
    )


async def run_migration():
    engine = create_async_engine(get_db_url(), echo=False)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(lambda c: DynamicDialogBinding.__table__.create(c, checkfirst=True))
            await conn.execute(text("CREATE SEQUENCE IF NOT EXISTS dynamic_dialog_bindings_id_seq"))
            await conn.execute(
                text(
                    """
                    ALTER TABLE dynamic_dialog_bindings
                    ALTER COLUMN id
                    SET DEFAULT nextval('dynamic_dialog_bindings_id_seq'::regclass)
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    SELECT setval(
                        'dynamic_dialog_bindings_id_seq',
                        COALESCE((SELECT MAX(id) FROM dynamic_dialog_bindings), 1),
                        EXISTS (SELECT 1 FROM dynamic_dialog_bindings)
                    )
                    """
                )
            )

            normalized_tables: dict[str, int] = {}
            for table_name in DDID_TABLES:
                normalized_tables[table_name] = await _normalize_table_ddids(conn, table_name)

            inserted = await _backfill_registry(conn)

            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_feedbacks_ddid ON feedbacks (ddid)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_poll_answers_ddid ON poll_answers (ddid)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_service_tickets_ddid ON service_tickets (ddid)"))

            await _ensure_fk(
                conn,
                table_name="feedbacks",
                constraint_name="fk_feedbacks_ddid_dynamic_dialog_bindings",
            )
            await _ensure_fk(
                conn,
                table_name="poll_answers",
                constraint_name="fk_poll_answers_ddid_dynamic_dialog_bindings",
            )
            await _ensure_fk(
                conn,
                table_name="service_tickets",
                constraint_name="fk_service_tickets_ddid_dynamic_dialog_bindings",
            )

        logger.info("Таблица dynamic_dialog_bindings создана или уже существовала")
        logger.info(
            "Нормализация ddid: %s",
            ", ".join(f"{table}={count}" for table, count in normalized_tables.items()),
        )
        logger.info("Добавлено записей в реестр DDID: %s", inserted)
        logger.info("Внешние ключи для feedbacks, poll_answers и service_tickets настроены")
    finally:
        await engine.dispose()


def main():
    import asyncio

    try:
        asyncio.run(run_migration())
    except Exception as e:
        logger.exception("Ошибка миграции add_dynamic_dialog_bindings: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
