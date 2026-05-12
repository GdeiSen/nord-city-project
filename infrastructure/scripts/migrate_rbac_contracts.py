#!/usr/bin/env python3
"""
One-way migration from legacy users.role to RBAC.

Creates:
  - roles / permissions / role_permissions / user_roles
  - contracts / user_contracts

Then migrates current numeric users.role values into user_roles and drops users.role.
Application code after this migration must use RBAC only.
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

from shared.permissions import (  # noqa: E402
    ADMIN_DEFAULT_PERMISSIONS,
    ADMIN_ROLE_CODE,
    DEFAULT_PERMISSIONS,
    EVERYONE_DEFAULT_PERMISSIONS,
    EVERYONE_ROLE_CODE,
    SUPER_ADMIN_ROLE_CODE,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

LEGACY_ROLE_CODE_BY_ID = {
    0: "guest",
    10011: "lpr",
    20122: "ma",
    10014: "manager",
    10012: ADMIN_ROLE_CODE,
    10013: SUPER_ADMIN_ROLE_CODE,
}

LEGACY_ROLE_TITLES = {
    "guest": "Guest",
    "lpr": "User LPR",
    "ma": "User MA",
    "manager": "Manager",
    ADMIN_ROLE_CODE: "Admin",
    SUPER_ADMIN_ROLE_CODE: "Super Admin",
    EVERYONE_ROLE_CODE: "Everyone",
}


def get_db_url() -> str:
    host = os.getenv("DB_HOST", "127.0.0.1")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME", "nordcity_db")
    user = os.getenv("DB_USER", "nordcity_app")
    password = os.getenv("DB_PASSWORD", "")
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{name}"


async def _create_schema(conn) -> None:
    await conn.execute(text("CREATE SEQUENCE IF NOT EXISTS roles_id_seq"))
    await conn.execute(text("CREATE SEQUENCE IF NOT EXISTS permissions_id_seq"))
    await conn.execute(text("CREATE SEQUENCE IF NOT EXISTS contracts_id_seq"))
    await conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS roles (
                id INTEGER PRIMARY KEY DEFAULT nextval('roles_id_seq'::regclass),
                code VARCHAR(100) NOT NULL UNIQUE,
                name VARCHAR(150) NOT NULL,
                description TEXT NULL,
                is_system BOOLEAN NOT NULL DEFAULT FALSE,
                is_default BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
    )
    await conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS permissions (
                id INTEGER PRIMARY KEY DEFAULT nextval('permissions_id_seq'::regclass),
                code VARCHAR(150) NOT NULL UNIQUE,
                scope VARCHAR(80) NOT NULL,
                name VARCHAR(150) NOT NULL,
                description TEXT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
    )
    await conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS role_permissions (
                role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
                permission_id INTEGER NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                PRIMARY KEY (role_id, permission_id)
            )
            """
        )
    )
    await conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS user_roles (
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                PRIMARY KEY (user_id, role_id)
            )
            """
        )
    )
    await conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS contracts (
                id INTEGER PRIMARY KEY DEFAULT nextval('contracts_id_seq'::regclass),
                number VARCHAR(120) NOT NULL UNIQUE,
                title VARCHAR(250) NULL,
                status VARCHAR(40) NOT NULL DEFAULT 'ACTIVE',
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
    )
    await conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS user_contracts (
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                contract_id INTEGER NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
                is_primary BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                PRIMARY KEY (user_id, contract_id)
            )
            """
        )
    )


async def _seed_roles_and_permissions(conn) -> None:
    for item in DEFAULT_PERMISSIONS:
        await conn.execute(
            text(
                """
                INSERT INTO permissions (code, scope, name, description)
                VALUES (:code, :scope, :name, :description)
                ON CONFLICT (code) DO UPDATE
                SET scope = EXCLUDED.scope,
                    name = EXCLUDED.name,
                    description = EXCLUDED.description,
                    updated_at = now()
                """
            ),
            {**item, "description": item.get("description")},
        )

    role_codes = [EVERYONE_ROLE_CODE, "guest", "lpr", "ma", "manager", ADMIN_ROLE_CODE, SUPER_ADMIN_ROLE_CODE]
    for code in role_codes:
        await conn.execute(
            text(
                """
                INSERT INTO roles (code, name, is_system, is_default)
                VALUES (:code, :name, :is_system, :is_default)
                ON CONFLICT (code) DO UPDATE
                SET name = EXCLUDED.name,
                    is_system = EXCLUDED.is_system,
                    is_default = EXCLUDED.is_default,
                    updated_at = now()
                """
            ),
            {
                "code": code,
                "name": LEGACY_ROLE_TITLES.get(code, code),
                "is_system": code in {EVERYONE_ROLE_CODE, ADMIN_ROLE_CODE, SUPER_ADMIN_ROLE_CODE},
                "is_default": code == EVERYONE_ROLE_CODE,
            },
        )

    await _grant_permissions(conn, EVERYONE_ROLE_CODE, EVERYONE_DEFAULT_PERMISSIONS)
    await _grant_permissions(conn, ADMIN_ROLE_CODE, ADMIN_DEFAULT_PERMISSIONS)
    await _grant_permissions(conn, SUPER_ADMIN_ROLE_CODE, {item["code"] for item in DEFAULT_PERMISSIONS})


async def _grant_permissions(conn, role_code: str, permission_codes: set[str]) -> None:
    for permission_code in sorted(permission_codes):
        await conn.execute(
            text(
                """
                INSERT INTO role_permissions (role_id, permission_id)
                SELECT r.id, p.id
                FROM roles r
                JOIN permissions p ON p.code = :permission_code
                WHERE r.code = :role_code
                ON CONFLICT DO NOTHING
                """
            ),
            {"role_code": role_code, "permission_code": permission_code},
        )


async def _migrate_users(conn) -> None:
    role_column = await conn.execute(
        text(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = 'users' AND column_name = 'role'
            """
        )
    )
    if role_column.first() is None:
        logger.info("users.role already removed; skipping legacy role transfer.")
        return

    for legacy_role_id, role_code in LEGACY_ROLE_CODE_BY_ID.items():
        await conn.execute(
            text(
                """
                INSERT INTO user_roles (user_id, role_id)
                SELECT u.id, r.id
                FROM users u
                JOIN roles r ON r.code = :role_code
                WHERE COALESCE(u.role, 0) = :legacy_role_id
                ON CONFLICT DO NOTHING
                """
            ),
            {"legacy_role_id": legacy_role_id, "role_code": role_code},
        )

    await conn.execute(
        text(
            """
            INSERT INTO user_roles (user_id, role_id)
            SELECT u.id, r.id
            FROM users u
            JOIN roles r ON r.code = 'guest'
            WHERE u.id NOT IN (SELECT user_id FROM user_roles)
            ON CONFLICT DO NOTHING
            """
        )
    )
    await conn.execute(text("ALTER TABLE users DROP COLUMN IF EXISTS role"))


async def main() -> None:
    missing = [name for name in ("DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD") if not os.getenv(name)]
    if missing:
        raise RuntimeError(f"Не заданы переменные окружения: {', '.join(missing)}")

    engine = create_async_engine(get_db_url(), echo=False)
    async with engine.begin() as conn:
        await _create_schema(conn)
        await _seed_roles_and_permissions(conn)
        await _migrate_users(conn)
    await engine.dispose()
    logger.info("RBAC/contracts migration completed.")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
