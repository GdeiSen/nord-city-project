# MinIO on Ubuntu

This guide installs `MinIO` as a system service on Ubuntu and prepares `.env` for Nord City.

## Quick setup (recommended)

If your project `.env` is already filled, you can let the repository script install
and configure MinIO automatically:

```bash
sudo python3 infrastructure/scripts/setup_minio_service.py
```

The script reads `STORAGE_S3_*` values from the project `.env`.

What it does:

- downloads the `minio` binary if it is missing
- creates the `minio` system user and directories
- writes `/etc/minio/minio.env`
- writes `/etc/systemd/system/minio.service`
- restarts the service
- creates the configured bucket (when the Python `minio` package is installed)

The manual steps below are still useful if you want to inspect or customize the setup.

## 1. Create system user

```bash
sudo useradd --system --home /var/lib/minio --shell /usr/sbin/nologin minio
sudo mkdir -p /var/lib/minio/data
sudo mkdir -p /etc/minio
sudo chown -R minio:minio /var/lib/minio
```

## 2. Install MinIO binary

```bash
curl -fsSL https://dl.min.io/server/minio/release/linux-amd64/minio \
  -o /tmp/minio
chmod +x /tmp/minio
sudo mv /tmp/minio /usr/local/bin/minio
```

Verify:

```bash
minio --version
```

## 3. Create MinIO environment file

```bash
sudo nano /etc/minio/minio.env
```

Example:

```bash
MINIO_ROOT_USER=nordcity_minio
MINIO_ROOT_PASSWORD=change_this_to_a_long_random_secret
MINIO_VOLUMES=/var/lib/minio/data
MINIO_OPTS="--console-address :9001"
```

Protect it:

```bash
sudo chmod 600 /etc/minio/minio.env
sudo chown minio:minio /etc/minio/minio.env
```

## 4. Create systemd unit

```bash
sudo nano /etc/systemd/system/minio.service
```

Use:

```ini
[Unit]
Description=MinIO
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
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable minio
sudo systemctl start minio
sudo systemctl status minio
```

## 5. Open ports (if needed)

If the application runs on the same host, you can keep MinIO bound locally via reverse proxy or firewall.

For direct access:

```bash
sudo ufw allow 9000/tcp
sudo ufw allow 9001/tcp
```

- `9000` = S3 API
- `9001` = MinIO console

## 6. Create bucket

Open the MinIO console:

- [http://YOUR_SERVER_IP:9001](http://YOUR_SERVER_IP:9001)

Login with `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD`.

Create bucket:

- `nord-city-storage`

If `STORAGE_S3_AUTO_CREATE_BUCKET=true`, `storage_service` can create it automatically on first start.

## 7. Configure Nord City `.env`

In the project root `.env`:

```bash
MEDIA_SERVICE_HTTP_URL=http://127.0.0.1:8004
STORAGE_SERVICE_HTTP_URL=http://127.0.0.1:8004

STORAGE_S3_ENDPOINT=127.0.0.1:9000
STORAGE_S3_PUBLIC_ENDPOINT=127.0.0.1:9000
STORAGE_S3_ACCESS_KEY=nordcity_minio
STORAGE_S3_SECRET_KEY=change_this_to_a_long_random_secret
STORAGE_S3_BUCKET=nord-city-storage
STORAGE_S3_SECURE=false
STORAGE_S3_PUBLIC_SECURE=false
STORAGE_S3_PRESIGNED_EXPIRY_SECONDS=900
STORAGE_S3_AUTO_CREATE_BUCKET=true
```

If MinIO is behind HTTPS and a domain, set:

```bash
STORAGE_S3_ENDPOINT=127.0.0.1:9000
STORAGE_S3_PUBLIC_ENDPOINT=https://minio.your-domain.com
STORAGE_S3_SECURE=true
STORAGE_S3_PUBLIC_SECURE=true
```

## 7.1. MinIO CORS for direct browser uploads

If the frontend uploads directly to MinIO using presigned URLs, the bucket must allow CORS for your site.

Configure this in the MinIO console or with `mc` so that your site origin is allowed for:

- `PUT`
- `GET`
- `HEAD`

And at minimum the headers:

- `Content-Type`
- `ETag`

## 8. Install Python dependency

After pulling the storage rewrite:

```bash
pip install -r requirements.txt
```

This installs the `minio` Python SDK required by `storage_service`.

## 9. Restart Nord City services

After `.env` is updated:

```bash
python3 orchestrator.py --kill
python3 orchestrator.py
```

Or restart only the affected services:

```bash
sudo systemctl restart minio
```

Then restart Nord City `storage_service`, `web_service`, and `bot_service`.
