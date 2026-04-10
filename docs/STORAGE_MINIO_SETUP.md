# Storage + MinIO Setup

This document describes the final Nord City storage architecture after the
full migration to `storage_service` + `MinIO`.

## Architecture

- `storage_service` is the business gateway for files.
- Files are uploaded from the browser directly to MinIO using presigned `PUT` URLs.
- `storage_service` only creates upload sessions and validates completed uploads.
- Permanent public file URLs stay inside the platform and are served through:
  `https://<public-api>/storage/<path>`
- `storage_files` in the database stores metadata, ownership, category, and links.

This means:

- MinIO is used as the object backend.
- `web_service` does not proxy upload bytes.
- `web_service` keeps the stable public file URL but redirects reads to a
  short-lived signed MinIO URL, so the file bytes are read directly from MinIO.

## Required Environment Variables

Use the root project `.env`.

```env
STORAGE_SERVICE_HOST=127.0.0.1
STORAGE_SERVICE_PORT=8004
STORAGE_SERVICE_HTTP_URL=http://127.0.0.1:8004
STORAGE_SERVICE_TIMEOUT=30
STORAGE_MAX_UPLOAD_SIZE=26214400

STORAGE_S3_ENDPOINT=127.0.0.1:9000
STORAGE_S3_SECURE=false

STORAGE_S3_PUBLIC_ENDPOINT=uploads.your-domain.com
STORAGE_S3_PUBLIC_SECURE=true

STORAGE_S3_ACCESS_KEY=replace_me
STORAGE_S3_SECRET_KEY=replace_me
STORAGE_S3_BUCKET=nord-city-storage
STORAGE_S3_REGION=
STORAGE_S3_PRESIGNED_EXPIRY_SECONDS=900
STORAGE_S3_AUTO_CREATE_BUCKET=true

PUBLIC_API_BASE_URL=https://your-domain.com/api/v1
NEXT_PUBLIC_API_URL=https://your-domain.com/api/v1
CORS_ORIGINS=https://your-domain.com,http://localhost:3000
```

Notes:

- `STORAGE_S3_ENDPOINT` is the internal address used by `storage_service`.
- `STORAGE_S3_PUBLIC_ENDPOINT` is the external host used in presigned upload URLs.
- `CORS_ORIGINS` must contain frontend origins, not the API origin.
- `PUBLIC_API_BASE_URL` and `NEXT_PUBLIC_API_URL` should point to the same public API.

## Recommended Public Topology

Recommended external layout:

- `your-domain.com` -> site + API
- `uploads.your-domain.com` -> MinIO S3 API
- `minio-console.your-domain.com` -> MinIO console (optional)

Recommended internal layout:

- `storage_service` -> `127.0.0.1:8004`
- `MinIO API` -> `127.0.0.1:9000`
- `MinIO Console` -> `127.0.0.1:9001`

## Install MinIO on Ubuntu

### 1. Install the binary

```bash
curl -fsSL https://dl.min.io/server/minio/release/linux-amd64/minio -o /tmp/minio
chmod +x /tmp/minio
sudo mv /tmp/minio /usr/local/bin/minio
/usr/local/bin/minio --version
```

### 2. Create the service user and directories

```bash
sudo groupadd --system minio || true
sudo useradd --system --gid minio --home /var/lib/minio --shell /usr/sbin/nologin minio || true

sudo mkdir -p /var/lib/minio/data
sudo mkdir -p /etc/minio

sudo chown -R minio:minio /var/lib/minio
sudo chown -R minio:minio /etc/minio
sudo chmod 750 /var/lib/minio
sudo chmod 750 /var/lib/minio/data
sudo chmod 750 /etc/minio
```

### 3. Create `/etc/minio/minio.env`

```bash
cat <<'EOF' | sudo tee /etc/minio/minio.env >/dev/null
MINIO_ROOT_USER="replace_me"
MINIO_ROOT_PASSWORD="replace_me"
MINIO_VOLUMES="/var/lib/minio/data"
MINIO_OPTS="--address 127.0.0.1:9000 --console-address 127.0.0.1:9001"
MINIO_SERVER_URL="https://uploads.your-domain.com"
EOF

sudo chown minio:minio /etc/minio/minio.env
sudo chmod 600 /etc/minio/minio.env
```

Important:

- `MINIO_ROOT_USER` must match `STORAGE_S3_ACCESS_KEY`
- `MINIO_ROOT_PASSWORD` must match `STORAGE_S3_SECRET_KEY`
- `MINIO_SERVER_URL` must be a plain URL, not markdown, and must be externally reachable

### 4. Run MinIO

#### Option A: systemd host (recommended)

Create the unit:

```bash
cat <<'EOF' | sudo tee /etc/systemd/system/minio.service >/dev/null
[Unit]
Description=MinIO Object Storage
Documentation=https://min.io/docs/minio/linux/index.html
Wants=network-online.target
After=network-online.target

[Service]
User=minio
Group=minio
EnvironmentFile=/etc/minio/minio.env
ExecStart=/usr/local/bin/minio server $MINIO_VOLUMES $MINIO_OPTS
Restart=always
RestartSec=5
LimitNOFILE=65536
TasksMax=infinity
TimeoutStopSec=infinity
SendSIGKILL=no

[Install]
WantedBy=multi-user.target
EOF
```

Start it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable minio
sudo systemctl restart minio
sudo systemctl status minio
```

#### Option B: container / workspace without systemd

If your environment is a container or coder workspace where `systemd` is not PID 1:

```bash
sudo bash -lc 'set -a; source /etc/minio/minio.env; set +a; nohup /usr/local/bin/minio server "$MINIO_VOLUMES" $MINIO_OPTS >/tmp/minio.log 2>&1 &'
```

Check it:

```bash
ps aux | grep minio
curl http://127.0.0.1:9000/minio/health/live
sudo tail -n 100 /tmp/minio.log
```

## MinIO CORS

For direct browser uploads via presigned URLs, the bucket must allow:

- methods: `PUT`, `GET`, `HEAD`
- origin: your frontend origin(s), for example `https://your-domain.com`
- headers: at minimum `Content-Type`, `ETag`

If CORS is missing, presigned uploads will fail in the browser even though MinIO is reachable.

## Start Nord City Services

After MinIO is running and `.env` is filled:

```bash
python3 orchestrator.py
```

`storage_service` will create the bucket automatically if:

```env
STORAGE_S3_AUTO_CREATE_BUCKET=true
```

## Validation Checklist

### 1. MinIO responds internally

```bash
curl http://127.0.0.1:9000/minio/health/live
```

Expected: `200 OK`

### 2. Credentials match

The following values must be identical:

- `/etc/minio/minio.env` -> `MINIO_ROOT_USER`
- `/etc/minio/minio.env` -> `MINIO_ROOT_PASSWORD`
- project `.env` -> `STORAGE_S3_ACCESS_KEY`
- project `.env` -> `STORAGE_S3_SECRET_KEY`

If they differ, `storage_service` will fail on startup with:

- `InvalidAccessKeyId`
- `The Access Key Id you provided does not exist in our records`

### 3. Public upload endpoint is reachable

Open:

- `https://uploads.your-domain.com`

The domain must resolve and reach the MinIO S3 API.

### 4. Public file links stay inside Nord City

Stored files should be referenced like:

```text
https://your-domain.com/api/v1/storage/<path>
```

This is correct. Upload goes to MinIO, and `web_service` validates the file
before redirecting the client to a short-lived signed MinIO URL.

## What Not To Do

- Do not use `0.0.0.0` in `STORAGE_S3_PUBLIC_ENDPOINT`
- Do not append a random port to preview domains that already encode the port in the hostname
- Do not put markdown syntax inside `MINIO_SERVER_URL`
- Do not use different credentials in MinIO and the project `.env`
- Do not add the API origin to `CORS_ORIGINS` when what you need is the frontend origin
