"""
Nord City Media Service
=======================
HTTP service for storing and serving media files (images, documents, etc.).
Files are stored in a configurable directory on disk.
"""

import base64
import logging
import os
import signal
import sys
import uuid
from pathlib import Path
from typing import Any, Dict

import uvicorn
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.responses import FileResponse, JSONResponse

sys.path.append(os.path.join(os.path.dirname(__file__), '../../../'))

from config import get_config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Nord City Media Service",
    description="Media storage and serving for Nord City platform.",
    version="1.0.0",
)

# CORS for frontend to load images
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "HEAD", "OPTIONS"],
    allow_headers=["*"],
)

# Config will be loaded at startup
_config = None


def _get_config():
    global _config
    if _config is None:
        _config = get_config()
    return _config


def _safe_filename(original: str) -> str:
    """Sanitize filename: keep extension, replace unsafe chars."""
    if not original or not original.strip():
        return "file"
    # Get extension
    parts = original.rsplit(".", 1)
    if len(parts) == 2 and len(parts[1]) <= 6 and parts[1].isalnum():
        base, ext = parts
        ext = "." + ext.lower()
    else:
        base, ext = original, ""
    # Sanitize base: alphanumeric, dash, underscore only
    safe_base = "".join(c if c.isalnum() or c in "-_" else "_" for c in base[:64])
    if not safe_base:
        safe_base = "file"
    return safe_base + ext


def _ensure_storage_dir() -> Path:
    """Create storage directory if needed."""
    cfg = _get_config()
    cfg.storage_dir.mkdir(parents=True, exist_ok=True)
    return cfg.storage_dir


def _resolve_path(relative_path: str) -> Path:
    """Resolve relative path to absolute file path. Prevents path traversal."""
    storage = _ensure_storage_dir()
    path = (storage / relative_path).resolve()
    if not str(path).startswith(str(storage.resolve())):
        raise HTTPException(status_code=400, detail="Invalid path")
    return path


def _do_upload(file_content_b64: str, filename: str, content_type: str | None = None) -> Dict[str, Any]:
    """Internal upload logic. Returns {path, url}."""
    cfg = _get_config()
    try:
        content = base64.b64decode(file_content_b64)
    except Exception as e:
        raise ValueError(f"Invalid base64: {e}") from e
    if len(content) > cfg.max_upload_size:
        raise ValueError(f"File too large. Max size: {cfg.max_upload_size} bytes")
    safe = _safe_filename(filename)
    unique_name = f"{uuid.uuid4().hex}_{safe}"
    storage = _ensure_storage_dir()
    file_path = storage / unique_name
    try:
        file_path.write_bytes(content)
    except OSError as e:
        logger.error(f"Failed to write file {file_path}: {e}")
        raise RuntimeError("Failed to store file") from e
    return {"path": unique_name, "url": f"/media/{unique_name}"}


def _do_delete(path: str) -> Dict[str, Any]:
    """Internal delete logic. Returns {deleted: True, path} or raises."""
    path = path.lstrip("/")
    if path.startswith("media/"):
        path = path[6:].lstrip("/")
    abs_path = _resolve_path(path)
    if not abs_path.exists():
        raise FileNotFoundError("File not found")
    try:
        abs_path.unlink()
    except OSError as e:
        logger.error(f"Failed to delete file {abs_path}: {e}")
        raise RuntimeError("Failed to delete file") from e
    return {"deleted": True, "path": path}


# --- RPC models ---

class RPCRequest(BaseModel):
    service: str
    method: str
    params: Dict[str, Any] = {}


class RPCResponse(BaseModel):
    success: bool
    data: Any = None
    error: str | None = None


async def _rpc_handler(request: dict) -> dict:
    """RPC handler for media service methods."""
    service = request.get("service")
    method = request.get("method")
    params = request.get("params", {})

    if service != "media":
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
        if method == "delete":
            path = params.get("path", "")
            if not path:
                return {"success": False, "data": None, "error": "Missing path"}
            result = _do_delete(path)
            return {"success": True, "data": result, "error": None}
        return {"success": False, "data": None, "error": f"Unknown method: {method}"}
    except ValueError as e:
        return {"success": False, "data": None, "error": str(e)}
    except FileNotFoundError as e:
        return {"success": False, "data": None, "error": str(e)}
    except (RuntimeError, OSError) as e:
        logger.error(f"RPC media.{method} failed: {e}", exc_info=True)
        return {"success": False, "data": None, "error": str(e)}


# --- Endpoints ---


@app.post("/internal/rpc", response_model=RPCResponse)
async def rpc_endpoint(request: RPCRequest):
    """
    Internal RPC endpoint for media operations.
    Used by MediaClient (HttpRpcClient).
    """
    result = await _rpc_handler(request.model_dump())
    return result


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a file. Returns path and public URL for the stored file.
    """
    cfg = _get_config()

    # Validate size (stream and check)
    content = await file.read()
    if len(content) > cfg.max_upload_size:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max size: {cfg.max_upload_size} bytes",
        )

    # Generate unique filename
    safe = _safe_filename(file.filename or "file")
    unique_name = f"{uuid.uuid4().hex}_{safe}"
    storage = _ensure_storage_dir()
    file_path = storage / unique_name

    try:
        file_path.write_bytes(content)
    except OSError as e:
        logger.error(f"Failed to write file {file_path}: {e}")
        raise HTTPException(status_code=500, detail="Failed to store file")

    # URL path for serving
    url_path = f"/media/{unique_name}"
    return JSONResponse(
        content={
            "path": unique_name,
            "url": url_path,
        }
    )


@app.get("/media/{file_path:path}")
async def serve_media(file_path: str):
    """
    Serve a stored media file by path.
    """
    try:
        abs_path = _resolve_path(file_path)
    except HTTPException:
        raise
    if not abs_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    # Content-Type from extension
    suffix = abs_path.suffix.lower()
    media_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".svg": "image/svg+xml",
        ".pdf": "application/pdf",
    }
    media_type = media_types.get(suffix, "application/octet-stream")

    return FileResponse(abs_path, media_type=media_type)


@app.delete("/media/{file_path:path}")
async def delete_media(file_path: str):
    """
    Delete a stored media file by path.
    """
    try:
        abs_path = _resolve_path(file_path)
    except HTTPException:
        raise
    if not abs_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    try:
        abs_path.unlink()
    except OSError as e:
        logger.error(f"Failed to delete file {abs_path}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete file")

    return JSONResponse(content={"deleted": True, "path": file_path})


@app.get("/health")
async def health_check():
    """Health check for the media service."""
    storage = _ensure_storage_dir()
    writable = os.access(storage, os.W_OK)
    return {
        "status": "healthy" if writable else "degraded",
        "service": "media_service",
        "storage_writable": writable,
        "storage_dir": str(storage),
    }


def signal_handler(signum, frame):
    logger.info(f"Received signal {signum}")


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    cfg = get_config()
    host = os.getenv("MEDIA_SERVICE_HOST", "0.0.0.0")
    port = cfg.service.port

    logger.info(f"Starting Media Service on {host}:{port}")
    logger.info(f"Storage directory: {cfg.storage_dir}")

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        log_level="info",
        reload=False,
    )
