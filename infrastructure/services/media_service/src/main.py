"""
Nord City Storage Service
=========================
HTTP facade over MinIO (S3-compatible storage).
The public HTTP/RPC API stays compatible with the existing storage/media layer.
"""

import base64
import io
import logging
import mimetypes
import os
import signal
import sys
import uuid
from datetime import timedelta
from pathlib import Path
from typing import Any, AsyncIterator, Dict

import uvicorn
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from minio import Minio
from minio.error import S3Error
from pydantic import BaseModel

sys.path.append(os.path.join(os.path.dirname(__file__), "../../../"))

from config import get_config
from shared.constants import StorageFileKind

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Nord City Storage Service",
    description="MinIO-backed file storage and serving for Nord City platform.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

_config = None
_backend = None


def _get_config():
    global _config
    if _config is None:
        _config = get_config()
    return _config


def _get_backend():
    global _backend
    if _backend is None:
        _backend = MinioStorageBackend(_get_config())
    return _backend


def _safe_filename(original: str) -> str:
    if not original or not original.strip():
        return "file"

    parts = original.rsplit(".", 1)
    if len(parts) == 2 and len(parts[1]) <= 10 and parts[1].isalnum():
        base, ext = parts
        ext = "." + parts[1].lower()
    else:
        base, ext = original, ""

    safe_base = "".join(c if c.isalnum() or c in "-_" else "_" for c in base[:96])
    if not safe_base:
        safe_base = "file"
    return safe_base + ext


def _normalize_object_name(value: str) -> str:
    path = str(value or "").strip().lstrip("/")
    if path.startswith("media/"):
        path = path[6:].lstrip("/")
    if path.startswith("storage/"):
        path = path[8:].lstrip("/")
    if not path or ".." in path or path.endswith("/"):
        raise HTTPException(status_code=400, detail="Invalid path")
    return path


def _detect_content_type(filename: str, explicit_content_type: str | None = None) -> str:
    content_type = str(explicit_content_type or "").strip().lower()
    if content_type:
        return content_type
    guessed, _ = mimetypes.guess_type(filename or "")
    return guessed or "application/octet-stream"


def _detect_file_kind(filename: str, content_type: str) -> str:
    ext = Path(filename or "").suffix.lower()
    if content_type.startswith("image/") or ext in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"}:
        return StorageFileKind.IMAGE
    if content_type.startswith("video/") or ext in {".mp4", ".webm", ".mov"}:
        return StorageFileKind.VIDEO
    if (
        content_type.startswith("text/")
        or content_type in {
            "application/pdf",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }
        or ext in {".pdf", ".doc", ".docx", ".txt", ".md", ".xls", ".xlsx", ".csv"}
    ):
        return StorageFileKind.DOCUMENT
    return StorageFileKind.OTHER


def _build_file_payload(unique_name: str, original_name: str, content_type: str, size_bytes: int) -> Dict[str, Any]:
    url_path = f"/storage/{unique_name}"
    safe_name = original_name or unique_name
    return {
        "path": unique_name,
        "url": url_path,
        "original_name": safe_name,
        "filename": safe_name,
        "content_type": content_type,
        "size_bytes": int(size_bytes),
        "extension": Path(safe_name).suffix.lower() or None,
        "kind": _detect_file_kind(safe_name, content_type),
    }


class MinioStorageBackend:
    """Thin adapter around MinIO preserving the old storage service contract."""

    def __init__(self, cfg):
        self.cfg = cfg
        self.client = Minio(
            endpoint=cfg.s3_endpoint,
            access_key=cfg.s3_access_key,
            secret_key=cfg.s3_secret_key,
            secure=cfg.s3_secure,
            region=cfg.s3_region or None,
        )
        self.public_client = Minio(
            endpoint=cfg.s3_public_endpoint,
            access_key=cfg.s3_access_key,
            secret_key=cfg.s3_secret_key,
            secure=cfg.s3_public_secure,
            region=cfg.s3_region or None,
        )

    def ensure_ready(self) -> None:
        bucket_exists = self.client.bucket_exists(self.cfg.s3_bucket)
        if bucket_exists:
            return
        if not self.cfg.s3_auto_create_bucket:
            raise RuntimeError(f"MinIO bucket '{self.cfg.s3_bucket}' does not exist")
        self.client.make_bucket(self.cfg.s3_bucket)
        logger.info("Created MinIO bucket '%s'", self.cfg.s3_bucket)

    def health(self) -> dict[str, Any]:
        try:
            bucket_exists = self.client.bucket_exists(self.cfg.s3_bucket)
            return {
                "status": "healthy" if bucket_exists else "degraded",
                "bucket_exists": bucket_exists,
            }
        except Exception as exc:
            logger.error("MinIO health check failed: %s", exc, exc_info=True)
            return {
                "status": "degraded",
                "bucket_exists": False,
                "error": str(exc),
            }

    def upload_bytes(
        self,
        *,
        content: bytes,
        filename: str,
        content_type: str | None = None,
    ) -> Dict[str, Any]:
        if len(content) > self.cfg.max_upload_size:
            raise ValueError(f"File too large. Max size: {self.cfg.max_upload_size} bytes")

        safe = _safe_filename(filename)
        object_name = f"{uuid.uuid4().hex}_{safe}"
        detected_content_type = _detect_content_type(filename, content_type)

        try:
            self.client.put_object(
                bucket_name=self.cfg.s3_bucket,
                object_name=object_name,
                data=io.BytesIO(content),
                length=len(content),
                content_type=detected_content_type,
            )
        except S3Error as exc:
            logger.error("Failed to upload object %s to MinIO: %s", object_name, exc, exc_info=True)
            raise RuntimeError("Failed to store file") from exc

        return _build_file_payload(object_name, filename, detected_content_type, len(content))

    def create_upload_session(
        self,
        *,
        filename: str,
        content_type: str | None = None,
        size_bytes: int = 0,
    ) -> Dict[str, Any]:
        if size_bytes and int(size_bytes) > self.cfg.max_upload_size:
            raise ValueError(f"File too large. Max size: {self.cfg.max_upload_size} bytes")

        safe = _safe_filename(filename)
        object_name = f"{uuid.uuid4().hex}_{safe}"
        detected_content_type = _detect_content_type(filename, content_type)

        try:
            upload_url = self.public_client.presigned_put_object(
                self.cfg.s3_bucket,
                object_name,
                expires=timedelta(seconds=self.cfg.presigned_expiry_seconds),
            )
            internal_upload_url = self.client.presigned_put_object(
                self.cfg.s3_bucket,
                object_name,
                expires=timedelta(seconds=self.cfg.presigned_expiry_seconds),
            )
        except S3Error as exc:
            logger.error("Failed to create presigned PUT URL for %s: %s", object_name, exc, exc_info=True)
            raise RuntimeError("Failed to create upload URL") from exc

        return {
            "path": object_name,
            "upload_url": upload_url,
            "internal_upload_url": internal_upload_url,
            "method": "PUT",
            "headers": {
                "Content-Type": detected_content_type,
            },
            "original_name": filename,
            "content_type": detected_content_type,
            "expires_in": self.cfg.presigned_expiry_seconds,
        }

    def complete_upload(
        self,
        *,
        path: str,
        original_name: str,
        content_type: str | None = None,
    ) -> Dict[str, Any]:
        object_name = _normalize_object_name(path)
        try:
            stat = self.client.stat_object(self.cfg.s3_bucket, object_name)
        except S3Error as exc:
            code = getattr(exc, "code", "")
            if code in {"NoSuchKey", "NoSuchObject"}:
                raise FileNotFoundError("File not found")
            logger.error("Failed to stat object %s: %s", object_name, exc, exc_info=True)
            raise RuntimeError("Failed to verify uploaded file") from exc

        detected_content_type = (
            str(content_type or "").strip().lower()
            or getattr(stat, "content_type", None)
            or _detect_content_type(original_name or object_name)
        )
        return _build_file_payload(
            object_name,
            original_name or object_name,
            detected_content_type,
            int(getattr(stat, "size", 0) or 0),
        )

    async def stream_object(self, object_name: str) -> tuple[AsyncIterator[bytes], str, dict[str, str]]:
        try:
            response = self.client.get_object(self.cfg.s3_bucket, object_name)
        except S3Error as exc:
            code = getattr(exc, "code", "")
            if code in {"NoSuchKey", "NoSuchObject"}:
                raise HTTPException(status_code=404, detail="File not found")
            logger.error("Failed to read object %s from MinIO: %s", object_name, exc, exc_info=True)
            raise HTTPException(status_code=502, detail="Storage service error")

        content_type = response.headers.get("Content-Type") or _detect_content_type(object_name)
        headers: dict[str, str] = {}
        content_length = response.headers.get("Content-Length")
        if content_length:
            headers["Content-Length"] = content_length
        etag = response.headers.get("ETag")
        if etag:
            headers["ETag"] = etag

        async def iterator() -> AsyncIterator[bytes]:
            try:
                for chunk in response.stream(64 * 1024):
                    if chunk:
                        yield chunk
            finally:
                response.close()
                response.release_conn()

        return iterator(), content_type, headers

    def delete_object(self, object_name: str) -> Dict[str, Any]:
        try:
            self.client.stat_object(self.cfg.s3_bucket, object_name)
        except S3Error as exc:
            code = getattr(exc, "code", "")
            if code in {"NoSuchKey", "NoSuchObject"}:
                raise FileNotFoundError("File not found")
            logger.error("Failed to stat object %s: %s", object_name, exc, exc_info=True)
            raise RuntimeError("Failed to access file") from exc

        try:
            self.client.remove_object(self.cfg.s3_bucket, object_name)
        except S3Error as exc:
            logger.error("Failed to delete object %s: %s", object_name, exc, exc_info=True)
            raise RuntimeError("Failed to delete file") from exc
        return {"deleted": True, "path": object_name}


def _do_upload(file_content_b64: str, filename: str, content_type: str | None = None) -> Dict[str, Any]:
    try:
        content = base64.b64decode(file_content_b64)
    except Exception as exc:
        raise ValueError(f"Invalid base64: {exc}") from exc
    return _get_backend().upload_bytes(
        content=content,
        filename=filename,
        content_type=content_type,
    )


def _do_delete(path: str) -> Dict[str, Any]:
    object_name = _normalize_object_name(path)
    return _get_backend().delete_object(object_name)


class RPCRequest(BaseModel):
    service: str
    method: str
    params: Dict[str, Any] = {}


class RPCResponse(BaseModel):
    success: bool
    data: Any = None
    error: str | None = None


async def _rpc_handler(request: dict) -> dict:
    service = request.get("service")
    method = request.get("method")
    params = request.get("params", {})

    if service not in {"media", "storage"}:
        return {"success": False, "data": None, "error": f"Unknown service: {service}"}
    if not method:
        return {"success": False, "data": None, "error": "Missing method"}

    try:
        if method == "upload":
            file_content_b64 = params.get("file_content_b64")
            filename = params.get("filename", "file")
            content_type = params.get("content_type")
            if not file_content_b64:
                return {"success": False, "data": None, "error": "Missing file_content_b64"}
            result = _do_upload(file_content_b64, filename, content_type)
            return {"success": True, "data": result, "error": None}
        if method == "create_upload_session":
            filename = params.get("filename", "file")
            content_type = params.get("content_type")
            size_bytes = int(params.get("size_bytes") or 0)
            result = _get_backend().create_upload_session(
                filename=filename,
                content_type=content_type,
                size_bytes=size_bytes,
            )
            return {"success": True, "data": result, "error": None}
        if method == "complete_upload":
            path = params.get("path", "")
            original_name = params.get("original_name", "") or path
            content_type = params.get("content_type")
            if not path:
                return {"success": False, "data": None, "error": "Missing path"}
            result = _get_backend().complete_upload(
                path=path,
                original_name=original_name,
                content_type=content_type,
            )
            return {"success": True, "data": result, "error": None}
        if method == "delete":
            path = params.get("path", "")
            if not path:
                return {"success": False, "data": None, "error": "Missing path"}
            result = _do_delete(path)
            return {"success": True, "data": result, "error": None}
        return {"success": False, "data": None, "error": f"Unknown method: {method}"}
    except ValueError as exc:
        return {"success": False, "data": None, "error": str(exc)}
    except FileNotFoundError as exc:
        return {"success": False, "data": None, "error": str(exc)}
    except (RuntimeError, OSError, HTTPException) as exc:
        logger.error("RPC storage.%s failed: %s", method, exc, exc_info=True)
        return {"success": False, "data": None, "error": str(exc)}


@app.on_event("startup")
async def startup_event():
    _get_backend().ensure_ready()
    logger.info(
        "Storage backend ready: endpoint=%s bucket=%s secure=%s",
        _get_config().s3_endpoint,
        _get_config().s3_bucket,
        _get_config().s3_secure,
    )


@app.post("/internal/rpc", response_model=RPCResponse)
async def rpc_endpoint(request: RPCRequest):
    return await _rpc_handler(request.model_dump())


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    try:
        result = _get_backend().upload_bytes(
            content=content,
            filename=file.filename or "file",
            content_type=file.content_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=413, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return JSONResponse(content=result)


async def _serve_file(file_path: str):
    object_name = _normalize_object_name(file_path)
    stream, media_type, headers = await _get_backend().stream_object(object_name)
    return StreamingResponse(stream, media_type=media_type, headers=headers)


@app.get("/storage/{file_path:path}")
async def serve_storage(file_path: str):
    return await _serve_file(file_path)


@app.get("/media/{file_path:path}")
async def serve_media(file_path: str):
    return await _serve_file(file_path)


async def _delete_file(file_path: str):
    object_name = _normalize_object_name(file_path)
    try:
        result = _get_backend().delete_object(object_name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return JSONResponse(content=result)


@app.delete("/storage/{file_path:path}")
async def delete_storage(file_path: str):
    return await _delete_file(file_path)


@app.delete("/media/{file_path:path}")
async def delete_media(file_path: str):
    return await _delete_file(file_path)


@app.get("/health")
async def health_check():
    cfg = _get_config()
    backend_status = _get_backend().health()
    return {
        "status": backend_status.get("status", "degraded"),
        "service": "storage_service",
        "backend": "minio",
        "bucket_exists": backend_status.get("bucket_exists", False),
        "bucket": cfg.s3_bucket,
        "endpoint": cfg.s3_endpoint,
        "secure": cfg.s3_secure,
        "error": backend_status.get("error"),
    }


def signal_handler(signum, frame):
    logger.info("Received signal %s", signum)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    cfg = get_config()
    host = os.getenv("STORAGE_SERVICE_HOST") or os.getenv("MEDIA_SERVICE_HOST", "0.0.0.0")
    port = cfg.service.port

    logger.info("Starting Storage Service on %s:%s", host, port)
    logger.info(
        "Using MinIO backend endpoint=%s bucket=%s secure=%s",
        cfg.s3_endpoint,
        cfg.s3_bucket,
        cfg.s3_secure,
    )

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        log_level="info",
        reload=False,
    )
