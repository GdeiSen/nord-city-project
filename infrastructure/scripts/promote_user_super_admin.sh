#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   bash infrastructure/scripts/promote_user_super_admin.sh gordey_senuta
# Optional env overrides:
#   POSTGRES_CONTAINER, DB_NAME, DB_USER, DB_HOST

TARGET_USERNAME="${1:-gordey_senuta}"
SUPER_ADMIN_ROLE_CODE="super_admin"

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
echo "[INFO] Назначаю пользователю '$TARGET_USERNAME' роль '$SUPER_ADMIN_ROLE_CODE'"

UPDATED_COUNT="$(docker exec -i "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -tA -c "
WITH target_user AS (
  SELECT id
  FROM users
  WHERE lower(replace(coalesce(username,''), '@', '')) = lower(replace('$ESCAPED_USERNAME', '@', ''))
),
target_role AS (
  SELECT id
  FROM roles
  WHERE code = '$SUPER_ADMIN_ROLE_CODE'
),
inserted AS (
  INSERT INTO user_roles (user_id, role_id)
  SELECT target_user.id, target_role.id
  FROM target_user
  CROSS JOIN target_role
  ON CONFLICT DO NOTHING
  RETURNING user_id
)
SELECT count(*) FROM target_user;
" | tr -d '[:space:]')"

if [[ "$UPDATED_COUNT" == "0" ]]; then
  echo "[WARN] Пользователь '$TARGET_USERNAME' не найден."
  echo "Проверьте username в таблице users."
  exit 1
fi

docker exec -i "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c "
SELECT u.id, u.username, string_agg(r.code, ', ' ORDER BY r.code) AS roles
FROM users u
LEFT JOIN user_roles ur ON ur.user_id = u.id
LEFT JOIN roles r ON r.id = ur.role_id
WHERE lower(replace(coalesce(u.username,''), '@', '')) = lower(replace('$ESCAPED_USERNAME', '@', ''))
GROUP BY u.id, u.username;
"

echo "[OK] Роль '$SUPER_ADMIN_ROLE_CODE' назначена."
