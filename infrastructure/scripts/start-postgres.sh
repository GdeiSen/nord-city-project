#!/bin/bash
# =============================================================================
# PostgreSQL Docker Setup Script for Nord City
# Uses infrastructure/.env for DB config
# Usage: ./start-postgres.sh [path/to/infrastructure]
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="${1:-$(dirname "$SCRIPT_DIR")}"
ENV_FILE="$INFRA_DIR/.env"
CONTAINER_NAME="postgres-nordcity"

# -----------------------------------------------------------------------------
# Load .env
# -----------------------------------------------------------------------------
if [ ! -f "$ENV_FILE" ]; then
    echo "[ERROR] .env not found at $ENV_FILE"
    exit 1
fi

echo "[INFO] Loading config from $ENV_FILE"
source "$ENV_FILE"

DB_USER="${DB_USER:-nordcity_app}"
DB_PASSWORD="${DB_PASSWORD:-}"
DB_NAME="${DB_NAME:-nordcity_db}"
DB_PORT="${DB_PORT:-5432}"

if [ -z "$DB_PASSWORD" ]; then
    echo "[ERROR] DB_PASSWORD is not set in .env"
    exit 1
fi

# -----------------------------------------------------------------------------
# Stop existing container (if any)
# -----------------------------------------------------------------------------
if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "[INFO] Stopping existing container..."
    docker stop "$CONTAINER_NAME" 2>/dev/null || true
    docker rm "$CONTAINER_NAME" 2>/dev/null || true
fi

# -----------------------------------------------------------------------------
# Run PostgreSQL container
# -----------------------------------------------------------------------------
echo "[INFO] Pulling postgres:16 image..."
docker pull postgres:16

echo "[INFO] Starting PostgreSQL container..."
docker run -d \
    --name "$CONTAINER_NAME" \
    -e POSTGRES_USER="$DB_USER" \
    -e POSTGRES_PASSWORD="$DB_PASSWORD" \
    -e POSTGRES_DB="$DB_NAME" \
    -p "${DB_PORT}:5432" \
    -v postgres-nordcity-data:/var/lib/postgresql/data \
    --restart unless-stopped \
    postgres:16

# -----------------------------------------------------------------------------
# Wait for PostgreSQL to be ready
# -----------------------------------------------------------------------------
echo "[INFO] Waiting for PostgreSQL to be ready..."
for i in {1..30}; do
    if docker exec "$CONTAINER_NAME" pg_isready -U "$DB_USER" -d "$DB_NAME" 2>/dev/null; then
        echo "[OK] PostgreSQL is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "[ERROR] PostgreSQL did not start in time"
        exit 1
    fi
    sleep 1
done

# -----------------------------------------------------------------------------
# Grant privileges (ensure user has full rights)
# -----------------------------------------------------------------------------
echo "[INFO] Granting privileges..."
docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 <<EOF
-- Full rights on database (owner already has these, but explicit for clarity)
GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};
-- Schema public
GRANT ALL ON SCHEMA public TO ${DB_USER};
GRANT CREATE ON SCHEMA public TO ${DB_USER};
-- Future tables in public
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO ${DB_USER};
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO ${DB_USER};
-- Existing objects (redundant for owner, safe to run)
DO \$\$
BEGIN
    EXECUTE 'GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ' || quote_ident('${DB_USER}');
    EXECUTE 'GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ' || quote_ident('${DB_USER}');
    EXECUTE 'GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO ' || quote_ident('${DB_USER}');
EXCEPTION WHEN OTHERS THEN NULL;
END \$\$;
EOF

echo ""
echo "============================================================"
echo "  PostgreSQL is running"
echo "============================================================"
echo "  Container:  $CONTAINER_NAME"
echo "  Database:   $DB_NAME"
echo "  User:       $DB_USER"
echo "  Port:       $DB_PORT"
echo "  Host:       ${DB_HOST:-127.0.0.1}"
echo ""
echo "  Connect: psql -h ${DB_HOST:-127.0.0.1} -p $DB_PORT -U $DB_USER -d $DB_NAME"
echo ""
echo "  If using Coder DinD, run: port-forward $DB_PORT"
echo "============================================================"