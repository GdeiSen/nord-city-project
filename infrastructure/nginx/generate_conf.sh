#!/bin/bash
# Генерирует nginx.conf из шаблона на основе .env
# Запуск: ./generate_conf.sh (из infrastructure/) или ./nginx/generate_conf.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$INFRA_DIR/.env"
TEMPLATE="$SCRIPT_DIR/nginx.conf.template"
OUTPUT="$SCRIPT_DIR/nginx.conf"

if [ -f "$ENV_FILE" ]; then
  set -a
  source "$ENV_FILE"
  set +a
fi

domain="${NGINX_DOMAIN:-nord-city.online}"
ssl_cert="${NGINX_SSL_CERT:-/etc/letsencrypt/live/nord-city.online/fullchain.pem}"
ssl_key="${NGINX_SSL_KEY:-/etc/letsencrypt/live/nord-city.online/privkey.pem}"
web_port="${WEB_SERVICE_PORT:-8003}"
site_port="${SITE_PORT:-3000}"

sed -e "s|{{ domain }}|$domain|g" \
    -e "s|{{ ssl_cert }}|$ssl_cert|g" \
    -e "s|{{ ssl_key }}|$ssl_key|g" \
    -e "s|{{ web_port }}|$web_port|g" \
    -e "s|{{ site_port }}|$site_port|g" \
    "$TEMPLATE" > "$OUTPUT"

echo "Generated $OUTPUT (domain=$domain, web_port=$web_port, site_port=$site_port)"
