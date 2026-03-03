# Nord City Storage Service

MinIO-backed facade service for file storage and file delivery.

## Purpose

- Stores files in `MinIO` (S3-compatible object storage)
- Preserves the existing HTTP and RPC contract for the rest of the platform
- Serves files through the same `/storage/{path}` and `/media/{path}` routes
- Keeps `web_service`, `bot_service` and all shared clients compatible
- Supports presigned direct uploads (`init -> PUT to MinIO -> complete`)

## API

| Method | Path | Description |
|-------|------|----------|
| POST | `/internal/rpc` | RPC endpoint for `MediaClient` / `storage_client` (`service=media|storage`, methods: `upload` (legacy), `create_upload_session`, `complete_upload`, `delete`) |
| POST | `/upload` | Direct multipart upload |
| GET | `/storage/{path}` | Stream file from MinIO |
| GET | `/media/{path}` | Legacy alias |
| DELETE | `/storage/{path}` | Delete file from MinIO |
| DELETE | `/media/{path}` | Legacy alias |
| GET | `/health` | Health check of MinIO connectivity and bucket availability |

## Environment

| Variable | Default | Description |
|------------|--------------|----------|
| `MEDIA_SERVICE_PORT` / `STORAGE_SERVICE_PORT` | `8004` | HTTP port |
| `MEDIA_SERVICE_HOST` / `STORAGE_SERVICE_HOST` | `0.0.0.0` | Bind host |
| `STORAGE_MAX_UPLOAD_SIZE` | `26214400` | Max upload size in bytes |
| `STORAGE_S3_ENDPOINT` | `127.0.0.1:9000` | MinIO endpoint |
| `STORAGE_S3_PUBLIC_ENDPOINT` | same as `STORAGE_S3_ENDPOINT` | Public endpoint used in presigned URLs |
| `STORAGE_S3_ACCESS_KEY` | `minioadmin` | MinIO access key |
| `STORAGE_S3_SECRET_KEY` | `minioadmin` | MinIO secret key |
| `STORAGE_S3_BUCKET` | `nord-city-storage` | Bucket for stored files |
| `STORAGE_S3_SECURE` | `false` | Use HTTPS for MinIO connection |
| `STORAGE_S3_PUBLIC_SECURE` | same as `STORAGE_S3_SECURE` | Use HTTPS in presigned URLs |
| `STORAGE_S3_PRESIGNED_EXPIRY_SECONDS` | `900` | Presigned URL TTL |
| `STORAGE_S3_AUTO_CREATE_BUCKET` | `true` | Create bucket automatically on startup |
| `STORAGE_S3_REGION` | empty | Optional region |

## Behaviour

- `storage_service` is now the permanent file gateway of the platform.
- Files are stored in MinIO as objects.
- `storage_path` remains the object key and stays compatible with `storage_files.storage_path`.
- Public URLs still point to `web_service` (`/api/v1/storage/...`) rather than exposing MinIO directly.
- `storage_files` in the database remains the source of metadata and relations.
- Browser uploads can now go directly to MinIO via presigned PUT URLs returned by `web_service`.
- For direct browser uploads, the MinIO bucket must allow CORS for your site origin.
- Ubuntu bootstrap script: `/Users/orca/Local/nord-city-project/infrastructure/scripts/setup_minio_service.py`
