#!/usr/bin/env python3
"""
Install and configure MinIO as a systemd service using the project .env file.

The script is intentionally idempotent:
- downloads the MinIO binary if it is missing
- creates the system user/group if needed
- writes /etc/minio/minio.env
- writes /etc/systemd/system/minio.service
- reloads systemd and restarts the service
- creates the configured bucket when the Python MinIO SDK is available

Run it as root:
    sudo python3 infrastructure/scripts/setup_minio_service.py
"""

from __future__ import annotations

import argparse
import os
import pwd
import grp
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import urlopen

try:
    from dotenv import dotenv_values
except ImportError:  # pragma: no cover - optional fallback
    dotenv_values = None

try:
    from minio import Minio
except ImportError:  # pragma: no cover - optional fallback
    Minio = None


DEFAULT_MINIO_BINARY_URL = "https://dl.min.io/server/minio/release/linux-amd64/minio"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ENV_FILE = PROJECT_ROOT / ".env"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Install and configure MinIO from the Nord City .env file.",
    )
    parser.add_argument(
        "--env-file",
        default=str(DEFAULT_ENV_FILE),
        help="Path to the project .env file (default: %(default)s)",
    )
    parser.add_argument(
        "--no-start",
        action="store_true",
        help="Write/update files but do not restart the MinIO service.",
    )
    return parser.parse_args()


def fail(message: str, code: int = 1) -> None:
    print(f"Error: {message}", file=sys.stderr)
    raise SystemExit(code)


def load_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        fail(f".env file was not found: {path}")

    if dotenv_values is not None:
        values = dotenv_values(path)
        return {
            str(key): str(value)
            for key, value in values.items()
            if key and value is not None
        }

    result: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key.strip()] = value.strip().strip("\"' ")
    return result


def env_value(values: dict[str, str], *keys: str, default: str = "") -> str:
    for key in keys:
        value = str(values.get(key, "")).strip()
        if value:
            return value
    return default


def parse_bool(value: str | None, default: bool = False) -> bool:
    raw = str(value or "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def parse_endpoint(raw_value: str, default_port: int = 9000) -> tuple[str, bool | None]:
    value = str(raw_value or "").strip()
    if not value:
        value = f"127.0.0.1:{default_port}"

    parsed = urlsplit(value)
    if parsed.scheme:
        hostport = (parsed.netloc or parsed.path).strip()
        secure = parsed.scheme.lower() == "https"
    else:
        hostport = value.rstrip("/")
        secure = None

    if ":" not in hostport:
        hostport = f"{hostport}:{default_port}"
    return hostport, secure


def build_url(hostport: str, secure: bool) -> str:
    scheme = "https" if secure else "http"
    return f"{scheme}://{hostport}"


def quote_env_value(value: str) -> str:
    escaped = str(value).replace("\\", "\\\\").replace("\"", "\\\"")
    return f"\"{escaped}\""


def split_host_port(hostport: str, default_port: int = 9000) -> tuple[str, int]:
    host = hostport
    port = default_port
    if hostport.count(":") == 1:
        host, raw_port = hostport.rsplit(":", 1)
        port = int(raw_port)
    elif hostport.startswith("[") and "]:" in hostport:
        host, raw_port = hostport.rsplit("]:", 1)
        host = f"{host}]"
        port = int(raw_port)
    return host or "127.0.0.1", port


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def ensure_group(name: str) -> None:
    try:
        grp.getgrnam(name)
    except KeyError:
        run(["groupadd", "--system", name])


def ensure_user(name: str, group: str, home: Path) -> None:
    try:
        pwd.getpwnam(name)
    except KeyError:
        run(
            [
                "useradd",
                "--system",
                "--gid",
                group,
                "--home",
                str(home),
                "--shell",
                "/usr/sbin/nologin",
                name,
            ]
        )


def ensure_directory(path: Path, owner: str, group: str, mode: int) -> None:
    path.mkdir(parents=True, exist_ok=True)
    os.chmod(path, mode)
    shutil.chown(path, user=owner, group=group)


def write_text_file(
    path: Path,
    content: str,
    mode: int,
    owner: str | None = None,
    group: str | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    os.chmod(path, mode)
    if owner or group:
        shutil.chown(path, user=owner, group=group)


def ensure_minio_binary(binary_path: Path, download_url: str) -> None:
    if binary_path.exists() and os.access(binary_path, os.X_OK):
        return

    binary_path.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(download_url) as response:
        with tempfile.NamedTemporaryFile(dir=binary_path.parent, delete=False) as tmp_file:
            shutil.copyfileobj(response, tmp_file)
            temp_path = Path(tmp_file.name)

    os.chmod(temp_path, 0o755)
    temp_path.replace(binary_path)
    print(f"Installed MinIO binary to {binary_path}")


def wait_for_port(hostport: str, timeout_seconds: int = 20) -> None:
    host, port = split_host_port(hostport)
    if host in {"0.0.0.0", "::", "[::]"}:
        host = "127.0.0.1"
    deadline = time.monotonic() + timeout_seconds
    last_error: OSError | None = None

    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host.strip("[]"), port), timeout=1.5):
                return
        except OSError as exc:
            last_error = exc
            time.sleep(1)

    if last_error is not None:
        raise RuntimeError(f"Timed out waiting for {hostport}: {last_error}")


def ensure_bucket(
    *,
    endpoint: str,
    secure: bool,
    access_key: str,
    secret_key: str,
    bucket: str,
) -> None:
    if Minio is None:
        print("MinIO Python SDK is not installed; skipping bucket creation check.")
        return

    client = Minio(
        endpoint=endpoint,
        access_key=access_key,
        secret_key=secret_key,
        secure=secure,
    )
    if client.bucket_exists(bucket):
        print(f"Bucket already exists: {bucket}")
        return

    client.make_bucket(bucket)
    print(f"Created bucket: {bucket}")


def main() -> None:
    args = parse_args()
    if os.geteuid() != 0:
        fail("this script must be run as root (try: sudo python3 ...)")

    if shutil.which("systemctl") is None:
        fail("systemctl was not found; this script expects systemd")

    env_path = Path(args.env_file).expanduser().resolve()
    env_values = load_env_file(env_path)

    minio_user = env_value(env_values, "MINIO_SYSTEM_USER", default="minio")
    minio_group = env_value(env_values, "MINIO_SYSTEM_GROUP", default=minio_user)
    minio_data_dir = Path(
        env_value(env_values, "MINIO_DATA_DIR", default="/var/lib/minio/data")
    )
    minio_home_dir = minio_data_dir.parent
    minio_config_dir = Path(
        env_value(env_values, "MINIO_CONFIG_DIR", default="/etc/minio")
    )
    minio_binary_path = Path(
        env_value(env_values, "MINIO_BINARY_PATH", default="/usr/local/bin/minio")
    )
    minio_binary_url = env_value(
        env_values,
        "MINIO_BINARY_URL",
        default=DEFAULT_MINIO_BINARY_URL,
    )
    minio_service_name = env_value(
        env_values,
        "MINIO_SYSTEMD_SERVICE",
        default="minio",
    )
    console_address = env_value(
        env_values,
        "MINIO_CONSOLE_ADDRESS",
        default=":9001",
    )

    access_key = env_value(
        env_values,
        "STORAGE_S3_ACCESS_KEY",
        "MINIO_ROOT_USER",
        default="minioadmin",
    )
    secret_key = env_value(
        env_values,
        "STORAGE_S3_SECRET_KEY",
        "MINIO_ROOT_PASSWORD",
        default="minioadmin",
    )
    bucket_name = env_value(
        env_values,
        "STORAGE_S3_BUCKET",
        default="nord-city-storage",
    )
    if not access_key or not secret_key:
        fail("STORAGE_S3_ACCESS_KEY and STORAGE_S3_SECRET_KEY must be set in .env")

    endpoint_raw = env_value(
        env_values,
        "STORAGE_S3_ENDPOINT",
        "MINIO_ENDPOINT",
        default="127.0.0.1:9000",
    )
    endpoint_hostport, endpoint_secure_from_scheme = parse_endpoint(endpoint_raw)
    endpoint_secure = (
        endpoint_secure_from_scheme
        if endpoint_secure_from_scheme is not None
        else parse_bool(env_values.get("STORAGE_S3_SECURE"), default=False)
    )

    public_endpoint_raw = env_value(
        env_values,
        "STORAGE_S3_PUBLIC_ENDPOINT",
        default=endpoint_raw,
    )
    public_hostport, public_secure_from_scheme = parse_endpoint(public_endpoint_raw)
    public_secure = (
        public_secure_from_scheme
        if public_secure_from_scheme is not None
        else parse_bool(
            env_values.get("STORAGE_S3_PUBLIC_SECURE"),
            default=endpoint_secure,
        )
    )
    public_server_url = build_url(public_hostport, public_secure)

    ensure_group(minio_group)
    ensure_user(minio_user, minio_group, minio_home_dir)
    ensure_directory(minio_home_dir, minio_user, minio_group, 0o750)
    ensure_directory(minio_data_dir, minio_user, minio_group, 0o750)
    ensure_directory(minio_config_dir, minio_user, minio_group, 0o750)
    ensure_minio_binary(minio_binary_path, minio_binary_url)

    minio_env_path = minio_config_dir / "minio.env"
    minio_env_content = "\n".join(
        [
            f"MINIO_ROOT_USER={quote_env_value(access_key)}",
            f"MINIO_ROOT_PASSWORD={quote_env_value(secret_key)}",
            f"MINIO_VOLUMES={quote_env_value(str(minio_data_dir))}",
            "MINIO_OPTS="
            + quote_env_value(
                f"--address {endpoint_hostport} --console-address {console_address}"
            ),
            f"MINIO_SERVER_URL={quote_env_value(public_server_url)}",
            "",
        ]
    )
    write_text_file(
        minio_env_path,
        minio_env_content,
        mode=0o600,
        owner=minio_user,
        group=minio_group,
    )

    service_file_path = Path("/etc/systemd/system") / f"{minio_service_name}.service"
    service_content = "\n".join(
        [
            "[Unit]",
            "Description=MinIO Object Storage",
            "Documentation=https://min.io/docs/minio/linux/index.html",
            "Wants=network-online.target",
            "After=network-online.target",
            "",
            "[Service]",
            f"User={minio_user}",
            f"Group={minio_group}",
            f"EnvironmentFile={minio_env_path}",
            f"ExecStart={minio_binary_path} server $MINIO_VOLUMES $MINIO_OPTS",
            "Restart=always",
            "RestartSec=5",
            "LimitNOFILE=65536",
            "TasksMax=infinity",
            "TimeoutStopSec=infinity",
            "SendSIGKILL=no",
            "",
            "[Install]",
            "WantedBy=multi-user.target",
            "",
        ]
    )
    write_text_file(service_file_path, service_content, mode=0o644)

    run(["systemctl", "daemon-reload"])
    run(["systemctl", "enable", minio_service_name])

    if not args.no_start:
        run(["systemctl", "restart", minio_service_name])
        wait_for_port(endpoint_hostport)
        try:
            ensure_bucket(
                endpoint=endpoint_hostport,
                secure=endpoint_secure,
                access_key=access_key,
                secret_key=secret_key,
                bucket=bucket_name,
            )
        except Exception as exc:
            print(f"Warning: failed to verify bucket '{bucket_name}': {exc}")

    print("")
    print("MinIO setup complete.")
    print(f"Service: {minio_service_name}")
    print(f"Binary:  {minio_binary_path}")
    print(f"API:     {build_url(endpoint_hostport, endpoint_secure)}")
    print(f"Public:  {public_server_url}")
    print(f"Bucket:  {bucket_name}")
    print("")
    print(
        "If the browser uploads files directly to MinIO, make sure "
        "bucket CORS allows PUT/GET/HEAD."
    )


if __name__ == "__main__":
    main()
