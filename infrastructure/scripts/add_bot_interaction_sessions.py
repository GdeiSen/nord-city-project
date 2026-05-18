#!/usr/bin/env python3
"""Create bot_interaction_sessions table for durable bot workflow state."""
import asyncio
import logging
import os
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent

env_path = PROJECT_ROOT / ".env"
if env_path.exists():
    try:
        from dotenv import load_dotenv

        load_dotenv(dotenv_path=env_path, override=False)
    except ImportError:
        pass

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def get_db_url() -> str:
    if os.getenv("DATABASE_URL"):
        return str(os.getenv("DATABASE_URL"))
    host = os.getenv("DB_HOST", "127.0.0.1")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME", "nordcity_db")
    user = os.getenv("DB_USER", "nordcity_app")
    password = os.getenv("DB_PASSWORD", "nordcity_app")
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{name}"


async def main() -> None:
    db_url = get_db_url()
    engine = create_async_engine(db_url)
    try:
        async with engine.begin() as conn:
            await conn.execute(text("CREATE SEQUENCE IF NOT EXISTS bot_interaction_sessions_id_seq"))
            await conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS bot_interaction_sessions (
                        id INTEGER PRIMARY KEY DEFAULT nextval('bot_interaction_sessions_id_seq'::regclass),
                        session_type VARCHAR(64) NOT NULL,
                        entity_type VARCHAR(64) NOT NULL,
                        entity_id BIGINT NOT NULL,
                        chat_id BIGINT NOT NULL,
                        owner_user_id BIGINT NOT NULL,
                        prompt_message_id BIGINT,
                        status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
                        meta JSON,
                        expires_at TIMESTAMPTZ,
                        created_at TIMESTAMPTZ DEFAULT now(),
                        updated_at TIMESTAMPTZ DEFAULT now()
                    )
                    """
                )
            )
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_bot_interaction_sessions_entity "
                    "ON bot_interaction_sessions (entity_type, entity_id)"
                )
            )
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_bot_interaction_sessions_chat "
                    "ON bot_interaction_sessions (session_type, chat_id, status)"
                )
            )
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_bot_interaction_sessions_owner "
                    "ON bot_interaction_sessions (session_type, owner_user_id, status)"
                )
            )
            await conn.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS uq_bot_interaction_sessions_active_chat "
                    "ON bot_interaction_sessions (session_type, chat_id) WHERE status = 'ACTIVE'"
                )
            )
            await conn.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS uq_bot_interaction_sessions_active_owner "
                    "ON bot_interaction_sessions (session_type, owner_user_id) WHERE status = 'ACTIVE'"
                )
            )
        logger.info("bot_interaction_sessions migration completed")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
