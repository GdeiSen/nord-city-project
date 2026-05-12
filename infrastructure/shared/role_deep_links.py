from __future__ import annotations

import base64
import hashlib
import hmac
import os
import re


ROLE_START_PAYLOAD_RE = re.compile(r"^r([0-9a-z]+)\.([A-Za-z0-9_-]{16})$")
_DEFAULT_JWT_SECRET = "your-secret-key-change-in-production"


def _get_secret() -> str:
    return (
        os.getenv("BOT_DEEP_LINK_SECRET")
        or os.getenv("JWT_SECRET_KEY")
        or ""
    ).strip()


def is_role_deep_link_configured() -> bool:
    secret = _get_secret()
    return bool(secret and secret != _DEFAULT_JWT_SECRET)


def _to_base36(value: int) -> str:
    if value < 0:
        raise ValueError("role_id must be non-negative")
    alphabet = "0123456789abcdefghijklmnopqrstuvwxyz"
    if value == 0:
        return "0"
    digits = []
    while value:
        value, remainder = divmod(value, 36)
        digits.append(alphabet[remainder])
    return "".join(reversed(digits))


def _from_base36(value: str) -> int:
    return int(value, 36)


def _signature(role_id: int) -> str:
    secret = _get_secret()
    if not secret:
        raise RuntimeError("BOT_DEEP_LINK_SECRET or JWT_SECRET_KEY must be configured")
    digest = hmac.new(
        secret.encode("utf-8"),
        f"role:{int(role_id)}".encode("utf-8"),
        hashlib.sha256,
    ).digest()[:12]
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def create_role_start_payload(role_id: int) -> str:
    normalized_role_id = int(role_id)
    return f"r{_to_base36(normalized_role_id)}.{_signature(normalized_role_id)}"


def verify_role_start_payload(payload: str | None) -> int | None:
    match = ROLE_START_PAYLOAD_RE.match((payload or "").strip())
    if not match:
        return None
    role_id = _from_base36(match.group(1))
    expected = _signature(role_id)
    if not hmac.compare_digest(expected, match.group(2)):
        return None
    return role_id
