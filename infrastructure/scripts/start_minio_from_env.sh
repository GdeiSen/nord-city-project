#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ENV_FILE:-$PROJECT_ROOT/.env}"
CONTAINER_NAME="${MINIO_CONTAINER_NAME:-nordcity-minio}"
DATA_DIR="${MINIO_DATA_DIR:-$PROJECT_ROOT/.data/minio}"
WORKSPACE_CONTAINER="${WORKSPACE_CONTAINER_NAME:-coder-fluctus-venti-taiga}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing env file: $ENV_FILE" >&2
  exit 1
fi

set -a
source "$ENV_FILE"
set +a

: "${STORAGE_S3_ACCESS_KEY:?STORAGE_S3_ACCESS_KEY is required}"
: "${STORAGE_S3_SECRET_KEY:?STORAGE_S3_SECRET_KEY is required}"
: "${STORAGE_S3_PUBLIC_ENDPOINT:?STORAGE_S3_PUBLIC_ENDPOINT is required}"

mkdir -p "$DATA_DIR"

if ! docker inspect "$WORKSPACE_CONTAINER" >/dev/null 2>&1; then
  echo "Workspace container not found: $WORKSPACE_CONTAINER" >&2
  echo "Set WORKSPACE_CONTAINER_NAME to the actual coder workspace container name." >&2
  exit 1
fi

docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true

docker run -d \
  --name "$CONTAINER_NAME" \
  --restart unless-stopped \
  --network "container:$WORKSPACE_CONTAINER" \
  -e "MINIO_ROOT_USER=$STORAGE_S3_ACCESS_KEY" \
  -e "MINIO_ROOT_PASSWORD=$STORAGE_S3_SECRET_KEY" \
  -e "MINIO_SERVER_URL=https://$STORAGE_S3_PUBLIC_ENDPOINT" \
  -v "$DATA_DIR:/data" \
  quay.io/minio/minio:latest \
  server /data \
  --address 127.0.0.1:9000 \
  --console-address 127.0.0.1:9001

echo "MinIO started as container: $CONTAINER_NAME"
echo "API:     http://127.0.0.1:9000"
echo "Console: http://127.0.0.1:9001"
