"""
Media utilities.
Extraction, validation, and conversion of media URLs.
"""

import os
import re
from typing import List

# Media path pattern: uuid_hex + _ + filename (e.g. a1b2c3d4_photo.jpg)
MEDIA_PATH_PATTERN = re.compile(r"^[a-f0-9]{32}_.+$")


def is_media_service_url(url: str, base_url: str | None = None) -> bool:
    """
    Check if URL points to our media service storage.
    If base_url is None, we check for /media/ prefix and valid path pattern.
    """
    if not url or not isinstance(url, str) or not url.strip():
        return False
    url = url.strip()
    # Must contain /media/ and have something after it
    if "/media/" not in url:
        return False
    parts = url.split("/media/", 1)
    if len(parts) != 2 or not parts[1]:
        return False
    path = parts[1].split("?")[0].strip()  # strip query params
    if not path or ".." in path or path.startswith("/"):
        return False
    # Path should match our format: uuid_filename.ext
    return bool(MEDIA_PATH_PATTERN.match(path))


def extract_media_path(url: str) -> str | None:
    """
    Extract storage path from a media service URL.
    Returns the path (e.g. uuid_filename.jpg) or None if not a valid media URL.
    """
    if not url or not isinstance(url, str):
        return None
    if "/media/" not in url:
        return None
    parts = url.split("/media/", 1)
    if len(parts) != 2 or not parts[1]:
        return None
    path = parts[1].split("?")[0].strip()
    if not path or ".." in path:
        return None
    return path if MEDIA_PATH_PATTERN.match(path) else None


def to_public_media_url(url: str) -> str | None:
    """
    Convert any media URL to a full public URL for external use (e.g. Telegram).
    Handles relative (/api/v1/media/xxx), internal (127.0.0.1), plain path, or already-public URLs.
    Returns None if URL cannot be converted.
    """
    if not url or not isinstance(url, str):
        return None
    url = url.strip()
    path = extract_media_path(url)
    if not path and MEDIA_PATH_PATTERN.match(url):
        path = url.split("/")[-1]
    if not path:
        return None
    base = os.getenv("PUBLIC_API_BASE_URL", "").rstrip("/")
    if not base:
        base = os.getenv("NEXT_PUBLIC_API_URL", "").rstrip("/")
    if not base:
        return None
    return f"{base}/media/{path}"


def get_removed_media_paths(old_urls: List[str], new_urls: List[str]) -> List[str]:
    """
    Compare old and new URL lists, return paths of media files that are no longer used.
    Only returns paths for URLs that belong to our media service.
    """
    old_set = set((u or "").strip() for u in (old_urls or []) if u)
    new_set = set((u or "").strip() for u in (new_urls or []) if u)
    removed_urls = old_set - new_set
    paths = []
    for url in removed_urls:
        path = extract_media_path(url)
        if path:
            paths.append(path)
    return paths
