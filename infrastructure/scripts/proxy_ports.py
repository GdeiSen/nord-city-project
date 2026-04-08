#!/usr/bin/env python3
"""
Small TCP port forwarder for workspace-local previews.

Default use case:
  python infrastructure/scripts/proxy_ports.py
    -> listens on 127.0.0.1:9000 and forwards to infra-minio:9000

Optional console proxy:
  python infrastructure/scripts/proxy_ports.py --with-console
    -> also proxies 127.0.0.1:9001 to infra-minio:9001

Generic mappings:
  python infrastructure/scripts/proxy_ports.py \
    --map 9000:infra-minio:9000 \
    --map 9001:infra-minio:9001
"""

from __future__ import annotations

import argparse
import asyncio
import signal
import sys
from dataclasses import dataclass


BUFFER_SIZE = 64 * 1024


@dataclass(frozen=True)
class PortMapping:
    listen_host: str
    listen_port: int
    target_host: str
    target_port: int

    @property
    def label(self) -> str:
        return f"{self.listen_host}:{self.listen_port} -> {self.target_host}:{self.target_port}"


def parse_mapping(spec: str, *, listen_host: str) -> PortMapping:
    parts = spec.split(":")
    if len(parts) != 3:
        raise argparse.ArgumentTypeError(
            f"Invalid mapping '{spec}'. Expected LISTEN_PORT:TARGET_HOST:TARGET_PORT."
        )

    listen_port_raw, target_host, target_port_raw = parts
    try:
        listen_port = int(listen_port_raw)
        target_port = int(target_port_raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Invalid port in mapping '{spec}'. Ports must be integers."
        ) from exc

    if not target_host.strip():
        raise argparse.ArgumentTypeError(
            f"Invalid mapping '{spec}'. Target host must not be empty."
        )

    return PortMapping(
        listen_host=listen_host,
        listen_port=listen_port,
        target_host=target_host.strip(),
        target_port=target_port,
    )


async def pipe_stream(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
) -> None:
    try:
        while True:
            chunk = await reader.read(BUFFER_SIZE)
            if not chunk:
                break
            writer.write(chunk)
            await writer.drain()
    except (ConnectionError, OSError):
        pass
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except (ConnectionError, OSError):
            pass


async def handle_client(
    client_reader: asyncio.StreamReader,
    client_writer: asyncio.StreamWriter,
    mapping: PortMapping,
    verbose: bool,
) -> None:
    peer = client_writer.get_extra_info("peername")
    if verbose:
        print(f"[proxy] accepted {peer} via {mapping.label}", flush=True)

    try:
        upstream_reader, upstream_writer = await asyncio.open_connection(
            mapping.target_host,
            mapping.target_port,
        )
    except (ConnectionError, OSError) as exc:
        print(
            f"[proxy] connect failed for {mapping.label}: {exc}",
            file=sys.stderr,
            flush=True,
        )
        client_writer.close()
        try:
            await client_writer.wait_closed()
        except (ConnectionError, OSError):
            pass
        return

    tasks = [
        asyncio.create_task(pipe_stream(client_reader, upstream_writer)),
        asyncio.create_task(pipe_stream(upstream_reader, client_writer)),
    ]

    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    for task in pending:
        task.cancel()
    await asyncio.gather(*pending, return_exceptions=True)
    await asyncio.gather(*done, return_exceptions=True)

    if verbose:
        print(f"[proxy] closed {peer} via {mapping.label}", flush=True)


async def start_server(mapping: PortMapping, verbose: bool) -> asyncio.AbstractServer:
    server = await asyncio.start_server(
        lambda reader, writer: handle_client(reader, writer, mapping, verbose),
        host=mapping.listen_host,
        port=mapping.listen_port,
    )
    print(f"[proxy] listening on {mapping.label}", flush=True)
    return server


async def run_proxy(mappings: list[PortMapping], verbose: bool) -> int:
    servers = [await start_server(mapping, verbose) for mapping in mappings]
    stop_event = asyncio.Event()

    def request_stop() -> None:
        print("[proxy] shutdown requested", flush=True)
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, request_stop)
        except NotImplementedError:
            pass

    await stop_event.wait()

    for server in servers:
        server.close()
    await asyncio.gather(*(server.wait_closed() for server in servers))
    return 0


def build_default_mappings(listen_host: str, with_console: bool) -> list[PortMapping]:
    mappings = [PortMapping(listen_host, 9000, "infra-minio", 9000)]
    if with_console:
        mappings.append(PortMapping(listen_host, 9001, "infra-minio", 9001))
    return mappings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Expose target TCP ports through the current workspace container.",
    )
    parser.add_argument(
        "--listen-host",
        default="127.0.0.1",
        help="Local host to bind inside the workspace. Default: 127.0.0.1",
    )
    parser.add_argument(
        "--map",
        action="append",
        default=[],
        metavar="LISTEN_PORT:TARGET_HOST:TARGET_PORT",
        help=(
            "TCP forwarding rule. Can be repeated. "
            "Default behavior without --map is 9000 -> infra-minio:9000."
        ),
    )
    parser.add_argument(
        "--with-console",
        action="store_true",
        help="Also proxy 9001 -> infra-minio:9001 when no explicit --map is provided.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Log accepted and closed client connections.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.map:
        mappings = [parse_mapping(spec, listen_host=args.listen_host) for spec in args.map]
    else:
        mappings = build_default_mappings(args.listen_host, args.with_console)

    try:
        return asyncio.run(run_proxy(mappings, args.verbose))
    except KeyboardInterrupt:
        return 130
    except OSError as exc:
        print(f"[proxy] startup failed: {exc}", file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
