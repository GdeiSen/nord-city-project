#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   bash infrastructure/scripts/promote_user_super_admin.sh gordey_senuta
# Optional env overrides:
#   POSTGRES_CONTAINER, DB_NAME, DB_USER, DB_HOST

TARGET_USERNAME="${1:-gordey_senuta}"
SUPER_ADMIN_ROLE_ID=10013

if [[ -f ".env" ]]; then
  # shellcheck disable=SC1091
  source .env
fi

DB_NAME="${DB_NAME:-nordcity_db}"
DB_USER="${DB_USER:-nordcity_app}"
DB_HOST="${DB_HOST:-postgres}"

resolve_container() {
  if [[ -n "${POSTGRES_CONTAINER:-}" ]]; then
    echo "$POSTGRES_CONTAINER"
    return
  fi

  if docker ps --format '{{.Names}}' | grep -qx "$DB_HOST"; then
    echo "$DB_HOST"
    return
  fi

  docker ps --format '{{.Names}}' | grep -E 'postgres|postgre|db' | head -n 1 || true
}

CONTAINER="$(resolve_container)"
if [[ -z "$CONTAINER" ]]; then
  echo "[ERROR] Не найден контейнер Postgres."
  echo "Укажите вручную: POSTGRES_CONTAINER=<container_name> bash $0 $TARGET_USERNAME"
  exit 1
fi

ESCAPED_USERNAME="${TARGET_USERNAME//\'/\'\'}"

echo "[INFO] Container: $CONTAINER"
echo "[INFO] DB: $DB_NAME, user: $DB_USER"
echo "[INFO] Обновляю роль пользователя '$TARGET_USERNAME' -> $SUPER_ADMIN_ROLE_ID"

UPDATED_COUNT="$(docker exec -i "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -tA -c "
WITH updated AS (
  UPDATE users
  SET role = $SUPER_ADMIN_ROLE_ID
  WHERE lower(replace(coalesce(username,''), '@', '')) = lower(replace('$ESCAPED_USERNAME', '@', ''))
  RETURNING id
)
SELECT count(*) FROM updated;
" | tr -d '[:space:]')"

if [[ "$UPDATED_COUNT" == "0" ]]; then
  echo "[WARN] Пользователь '$TARGET_USERNAME' не найден."
  echo "Проверьте username в таблице users."
  exit 1
fi

docker exec -i "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c "
SELECT id, username, role
FROM users
WHERE lower(replace(coalesce(username,''), '@', '')) = lower(replace('$ESCAPED_USERNAME', '@', ''));
"

echo "[OK] Роль обновлена на SUPER_ADMIN ($SUPER_ADMIN_ROLE_ID)."
