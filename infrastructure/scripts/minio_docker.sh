#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
ENV_FILE="${ENV_FILE:-${PROJECT_ROOT}/.env}"

ACTION="${1:-up}"
CONTAINER_NAME="${MINIO_CONTAINER_NAME:-nord-city-minio}"
MINIO_IMAGE="${MINIO_IMAGE:-quay.io/minio/minio:latest}"
MINIO_DATA_DIR="${MINIO_DATA_DIR:-${PROJECT_ROOT}/.data/minio}"
MINIO_API_BIND="${MINIO_API_BIND:-127.0.0.1:9000}"
MINIO_CONSOLE_BIND="${MINIO_CONSOLE_BIND:-127.0.0.1:9001}"

die() {
  echo "Error: $*" >&2
  exit 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "Missing required command: $1"
}

load_env() {
  [[ -f "${ENV_FILE}" ]] || die ".env file not found: ${ENV_FILE}"

  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a

  : "${STORAGE_S3_ACCESS_KEY:?STORAGE_S3_ACCESS_KEY is required in ${ENV_FILE}}"
  : "${STORAGE_S3_SECRET_KEY:?STORAGE_S3_SECRET_KEY is required in ${ENV_FILE}}"
  : "${STORAGE_S3_BUCKET:?STORAGE_S3_BUCKET is required in ${ENV_FILE}}"

  STORAGE_S3_ENDPOINT="${STORAGE_S3_ENDPOINT:-127.0.0.1:9000}"
  STORAGE_S3_PUBLIC_ENDPOINT="${STORAGE_S3_PUBLIC_ENDPOINT:-${STORAGE_S3_ENDPOINT}}"
  STORAGE_S3_SECURE="${STORAGE_S3_SECURE:-false}"
  STORAGE_S3_PUBLIC_SECURE="${STORAGE_S3_PUBLIC_SECURE:-${STORAGE_S3_SECURE}}"

  local public_scheme="http"
  if [[ "${STORAGE_S3_PUBLIC_SECURE,,}" == "true" ]]; then
    public_scheme="https"
  fi
  MINIO_SERVER_URL="${MINIO_SERVER_URL:-${public_scheme}://${STORAGE_S3_PUBLIC_ENDPOINT}}"
}

remove_existing_container() {
  if docker ps -a --format '{{.Names}}' | grep -Fxq "${CONTAINER_NAME}"; then
    docker rm -f "${CONTAINER_NAME}" >/dev/null
  fi
}

wait_for_minio() {
  local attempts=30

  for ((i = 1; i <= attempts; i++)); do
    if curl -fsS "http://${MINIO_API_BIND}/minio/health/live" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done

  docker logs "${CONTAINER_NAME}" --tail 50 >&2 || true
  die "MinIO did not become healthy on http://${MINIO_API_BIND}/minio/health/live"
}

cmd_up() {
  require_cmd docker
  require_cmd curl
  load_env

  mkdir -p "${MINIO_DATA_DIR}"
  remove_existing_container

  docker run -d \
    --name "${CONTAINER_NAME}" \
    --restart unless-stopped \
    -p "${MINIO_API_BIND}:9000" \
    -p "${MINIO_CONSOLE_BIND}:9001" \
    -e "MINIO_ROOT_USER=${STORAGE_S3_ACCESS_KEY}" \
    -e "MINIO_ROOT_PASSWORD=${STORAGE_S3_SECRET_KEY}" \
    -e "MINIO_SERVER_URL=${MINIO_SERVER_URL}" \
    -v "${MINIO_DATA_DIR}:/data" \
    "${MINIO_IMAGE}" \
    server /data --address ":9000" --console-address ":9001" >/dev/null

  wait_for_minio

  cat <<EOF
MinIO is running.
Container: ${CONTAINER_NAME}
API:       http://${MINIO_API_BIND}
Console:   http://${MINIO_CONSOLE_BIND}
Data dir:  ${MINIO_DATA_DIR}
Bucket:    ${STORAGE_S3_BUCKET}

Next:
  1. Start the app services.
  2. If the bucket does not exist yet, storage_service will create it when STORAGE_S3_AUTO_CREATE_BUCKET=true.
  3. Check logs with:
     ${SCRIPT_DIR}/minio_docker.sh logs
EOF
}

cmd_down() {
  require_cmd docker
  remove_existing_container
  echo "MinIO container removed: ${CONTAINER_NAME}"
}

cmd_logs() {
  require_cmd docker
  docker logs -f "${CONTAINER_NAME}"
}

cmd_status() {
  require_cmd docker
  docker ps --filter "name=${CONTAINER_NAME}" --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
}

case "${ACTION}" in
  up)
    cmd_up
    ;;
  down)
    cmd_down
    ;;
  logs)
    cmd_logs
    ;;
  status)
    cmd_status
    ;;
  *)
    cat <<EOF >&2
Usage: ${0##*/} [up|down|logs|status]

Examples:
  ${0##*/} up
  ${0##*/} down
EOF
    exit 1
    ;;
esac
