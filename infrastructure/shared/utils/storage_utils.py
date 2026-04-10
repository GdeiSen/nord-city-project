"""
Storage utilities.
Extraction, validation, and conversion of storage URLs.
"""

import os
import re
from typing import List

STORAGE_PATH_PATTERN = re.compile(r"^[a-f0-9]{32}_.+$")
STORAGE_URL_MARKER = "/storage/"


def normalize_public_api_base(base_url: str | None) -> str:
    """Normalize public API base URL for browser/Telegram use."""
    base = str(base_url or "").strip().rstrip("/")
    if not base:
        return ""
    if not re.match(r"^https?://", base, re.IGNORECASE):
        base = f"https://{base}"
    return base


def is_storage_service_url(url: str) -> bool:
    """Check if URL points to our storage service."""
    if not url or not isinstance(url, str) or not url.strip():
        return False
    path = extract_storage_path(url.strip())
    if not path or ".." in path or path.startswith("/"):
        return False
    return bool(STORAGE_PATH_PATTERN.match(path))


def extract_storage_path(url: str) -> str | None:
    """Extract a storage path (e.g. uuid_filename.jpg) from a storage URL."""
    if not url or not isinstance(url, str):
        return None
    if STORAGE_URL_MARKER not in url:
        return None
    parts = url.split(STORAGE_URL_MARKER, 1)
    if len(parts) != 2 or not parts[1]:
        return None
    path = parts[1].split("?")[0].strip()
    if not path or ".." in path:
        return None
    return path if STORAGE_PATH_PATTERN.match(path) else None


def to_public_storage_url(url: str) -> str | None:
    """
    Convert any storage URL/path to a full public URL for external use.
    Handles relative (/api/v1/storage/xxx), plain path, or already-public URLs.
    """
    if not url or not isinstance(url, str):
        return None
    candidate = url.strip()
    path = extract_storage_path(candidate)
    if not path and STORAGE_PATH_PATTERN.match(candidate):
        path = candidate.split("/")[-1]
    if not path:
        return None
    base = normalize_public_api_base(os.getenv("PUBLIC_API_BASE_URL", ""))
    if not base:
        base = normalize_public_api_base(os.getenv("NEXT_PUBLIC_API_URL", ""))
    if not base:
        return None
    return f"{base}/storage/{path}"


def get_removed_storage_paths(old_urls: List[str], new_urls: List[str]) -> List[str]:
    """Return storage paths that were removed when comparing two URL lists."""
    old_set = set((u or "").strip() for u in (old_urls or []) if u)
    new_set = set((u or "").strip() for u in (new_urls or []) if u)
    removed_urls = old_set - new_set
    paths = []
    for url in removed_urls:
        path = extract_storage_path(url)
        if path:
            paths.append(path)
    return paths
