#!/usr/bin/env python3
"""
Nord City Orchestrator
======================
Manages the lifecycle of all Nord City services (Python microservices + Next.js site)
from the project root. Each service runs in its own subprocess. Logs stream to terminal
or to logs/ when running in background.

Usage
-----
    python orchestrator.py                    # start ALL services, stream logs
    python orchestrator.py --services db,web  # start selected services
    python orchestrator.py --services site    # site + dependencies (web, db, bot, media)
    python orchestrator.py --service db       # start a SINGLE service in foreground
    python orchestrator.py --background       # run in background, logs → logs/
    python orchestrator.py --kill            # stop all background processes
    python orchestrator.py --info             # show running processes
    python orchestrator.py --list             # list available services

Services
--------
    db    — Database Service   (FastAPI HTTP RPC, port 8001)
    web   — Web Service        (FastAPI REST API, port 8003)
    bot   — Bot Service        (Telegram bot, port 8002)
    media — Media Service      (file storage & serving, port 8004)
    site  — Next.js Frontend   (port 3000)

Notes
-----
* PostgreSQL must be running separately.
* .env in project root is used for all services.
* Logs directory: project_root/logs/
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).parent.resolve()
INFRASTRUCTURE_ROOT = PROJECT_ROOT / "infrastructure"
sys.path.insert(0, str(INFRASTRUCTURE_ROOT))

from dotenv import load_dotenv  # noqa: E402

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
except ImportError:
    print(
        "ERROR: 'rich' package is required.\n  pip install rich>=13.7.0",
        file=sys.stderr,
    )
    sys.exit(1)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
STARTUP_DELAY_DEPENDENCY = 3
STARTUP_DELAY_DEFAULT = 1
SHUTDOWN_TIMEOUT = 5
LOG_BUFFER_SIZE = 120
REFRESH_RATE = 2

LOGS_DIR = PROJECT_ROOT / "logs"
STATE_FILE = LOGS_DIR / "orchestrator_state.json"


# ---------------------------------------------------------------------------
# Service state
# ---------------------------------------------------------------------------
class ServiceState(Enum):
    PENDING = "PENDING"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    STOPPED = "STOPPED"
    CRASHED = "CRASHED"


STATE_DISPLAY = {
    ServiceState.PENDING:  ("dim",       "⏳", "PENDING"),
    ServiceState.STARTING: ("yellow",    "🔄", "STARTING"),
    ServiceState.RUNNING:  ("green",     "●",  "RUNNING"),
    ServiceState.STOPPED:  ("dim",       "○",  "STOPPED"),
    ServiceState.CRASHED:  ("red bold",  "✖",  "CRASHED"),
}


# ---------------------------------------------------------------------------
# Service definitions
# ---------------------------------------------------------------------------
@dataclass
class ServiceInfo:
    """Static definition of a launchable service."""
    name: str
    alias: str
    description: str
    working_dir: Path
    command: List[str]
    port: Optional[int] = None
    health_url: Optional[str] = None
    depends_on: List[str] = field(default_factory=list)


@dataclass
class ServiceRuntime:
    """Mutable runtime state of a service."""
    info: ServiceInfo
    state: ServiceState = ServiceState.PENDING
    process: Optional[subprocess.Popen] = None
    started_at: Optional[datetime] = None
    log_buffer: deque = field(default_factory=lambda: deque(maxlen=LOG_BUFFER_SIZE))
    reader_thread: Optional[threading.Thread] = None
    exit_code: Optional[int] = None
    log_file_handle: Optional[object] = None


SERVICES: Dict[str, ServiceInfo] = {
    "db": ServiceInfo(
        name="Database Service",
        alias="db",
        description="FastAPI HTTP RPC — database operations",
        working_dir=INFRASTRUCTURE_ROOT / "services" / "database_service" / "src",
        command=[sys.executable, "main.py"],
        port=8001,
        health_url="http://127.0.0.1:{port}/health",
    ),
    "bot": ServiceInfo(
        name="Bot Service",
        alias="bot",
        description="Telegram bot + internal HTTP RPC",
        working_dir=INFRASTRUCTURE_ROOT / "services" / "bot_service" / "src",
        command=[sys.executable, "main.py"],
        port=8002,
        health_url="http://127.0.0.1:{port}/health",
        depends_on=["db"],
    ),
    "media": ServiceInfo(
        name="Media Service",
        alias="media",
        description="Media storage and serving",
        working_dir=INFRASTRUCTURE_ROOT / "services" / "media_service" / "src",
        command=[sys.executable, "main.py"],
        port=8004,
        health_url="http://127.0.0.1:{port}/health",
    ),
    "web": ServiceInfo(
        name="Web Service",
        alias="web",
        description="FastAPI REST API — frontend gateway",
        working_dir=INFRASTRUCTURE_ROOT / "services" / "web_service" / "src",
        command=[sys.executable, "main.py"],
        port=8003,
        health_url="http://127.0.0.1:{port}/health",
        depends_on=["db", "bot", "media"],
    ),
    "site": ServiceInfo(
        name="Next.js Site",
        alias="site",
        description="Next.js frontend",
        working_dir=PROJECT_ROOT / "web",
        command=["npm", "start"],
        port=3000,
        depends_on=["web"],
    ),
}

ALL_ALIASES = list(SERVICES.keys())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _resolve_start_order(requested: List[str]) -> List[str]:
    """Topological sort: include transitive dependencies, then order by deps first."""
    needed: set[str] = set()

    def _collect(alias: str):
        if alias in needed:
            return
        needed.add(alias)
        for dep in SERVICES[alias].depends_on:
            _collect(dep)

    for alias in requested:
        _collect(alias)

    ordered: List[str] = []
    visited: set[str] = set()

    def _visit(alias: str):
        if alias in visited:
            return
        visited.add(alias)
        for dep in SERVICES[alias].depends_on:
            if dep in needed:
                _visit(dep)
        ordered.append(alias)

    for alias in ALL_ALIASES:
        if alias in needed:
            _visit(alias)

    return ordered


def _format_uptime(started_at: Optional[datetime]) -> str:
    if started_at is None:
        return "-"
    delta = datetime.now() - started_at
    total = int(delta.total_seconds())
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def _update_ports_from_env():
    """Refresh port values from loaded environment variables."""
    for key, env_var, default in [
        ("db", "DATABASE_SERVICE_PORT", "8001"),
        ("web", "WEB_SERVICE_PORT", "8003"),
        ("bot", "BOT_SERVICE_PORT", "8002"),
        ("media", "MEDIA_SERVICE_PORT", "8004"),
        ("site", "SITE_PORT", "3000"),
    ]:
        if key in SERVICES:
            port_str = os.getenv(env_var, default)
            SERVICES[key].port = int(port_str)
            if SERVICES[key].health_url:
                SERVICES[key].health_url = f"http://127.0.0.1:{port_str}/health"


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------
class Orchestrator:
    """Manages service processes and streams their logs to terminal or files."""

    def __init__(
        self,
        services_to_start: List[str],
        env_file: Path,
        stream_logs: bool = True,
        log_to_files: bool = False,
        log_dir: Optional[Path] = None,
    ):
        self.console = Console()
        self.running = False
        self._shutdown_event = threading.Event()
        self.stream_logs = stream_logs
        self.log_to_files = log_to_files
        self.log_dir = log_dir or LOGS_DIR

        if env_file.exists():
            load_dotenv(env_file, override=True)
            self.console.print(f"[dim]Loaded environment from {env_file}[/dim]")
        else:
            self.console.print(f"[yellow]Warning: .env not found at {env_file}[/yellow]")

        _update_ports_from_env()

        self.child_env = os.environ.copy()
        self.child_env["PYTHONPATH"] = str(INFRASTRUCTURE_ROOT)
        self.child_env["PYTHONUNBUFFERED"] = "1"

        self.start_order = _resolve_start_order(services_to_start)
        auto_added = set(self.start_order) - set(services_to_start)
        if auto_added:
            self.console.print(f"[cyan]Auto-including dependencies: {', '.join(auto_added)}[/cyan]")

        self.services: Dict[str, ServiceRuntime] = {}
        for alias in self.start_order:
            self.services[alias] = ServiceRuntime(info=SERVICES[alias])

    def _read_output(self, runtime: ServiceRuntime, alias: str):
        """Background thread: read stdout and buffer; optionally stream to terminal."""
        proc = runtime.process
        if proc is None or proc.stdout is None:
            return
        try:
            for raw_line in iter(proc.stdout.readline, b""):
                text = raw_line.decode("utf-8", errors="replace").rstrip()
                if text:
                    runtime.log_buffer.append(text)
                    if self.stream_logs:
                        self.console.print(f"[{alias}] {text}")
        except (OSError, ValueError):
            pass

    def _start_service(self, alias: str) -> bool:
        """Launch a single service subprocess."""
        rt = self.services[alias]
        rt.state = ServiceState.STARTING

        if not rt.info.working_dir.exists():
            rt.state = ServiceState.CRASHED
            rt.log_buffer.append(f"ERROR: working dir missing: {rt.info.working_dir}")
            return False

        try:
            if self.log_to_files:
                self.log_dir.mkdir(parents=True, exist_ok=True)
                log_path = self.log_dir / f"{alias}.log"
                rt.log_file_handle = open(log_path, "a", encoding="utf-8")
                proc = subprocess.Popen(
                    rt.info.command,
                    cwd=str(rt.info.working_dir),
                    env=self.child_env,
                    stdout=rt.log_file_handle,
                    stderr=subprocess.STDOUT,
                    bufsize=1,
                )
            else:
                proc = subprocess.Popen(
                    rt.info.command,
                    cwd=str(rt.info.working_dir),
                    env=self.child_env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    bufsize=1,
                )
            rt.process = proc
            rt.started_at = datetime.now()
            rt.state = ServiceState.RUNNING

            if not self.log_to_files:
                reader = threading.Thread(
                    target=self._read_output, args=(rt, alias), daemon=True
                )
                reader.start()
                rt.reader_thread = reader

            return True
        except Exception as e:
            rt.state = ServiceState.CRASHED
            rt.log_buffer.append(f"Failed to start: {e}")
            return False

    def _check_processes(self):
        """Poll processes and update state if exited."""
        for rt in self.services.values():
            if rt.process is not None and rt.state == ServiceState.RUNNING:
                rc = rt.process.poll()
                if rc is not None:
                    rt.exit_code = rc
                    rt.state = ServiceState.CRASHED if rc != 0 else ServiceState.STOPPED

    def _save_state(self):
        """Save PIDs to state file for --kill/--info."""
        try:
            data = {
                "orchestrator_pid": os.getpid(),
                "services": {},
                "started_at": datetime.now().isoformat(),
            }
            for alias, rt in self.services.items():
                if rt.process is not None and rt.process.pid is not None:
                    data["services"][alias] = rt.process.pid
            self.log_dir.mkdir(parents=True, exist_ok=True)
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except OSError as e:
            self.console.print(f"[yellow]Warning: could not save state: {e}[/yellow]")

    def _remove_state(self):
        try:
            if STATE_FILE.exists():
                STATE_FILE.unlink()
        except OSError:
            pass

    def _shutdown_all(self):
        if self.log_to_files:
            self._remove_state()
        self.console.print("\n[yellow]Shutting down services...[/yellow]")
        for alias in reversed(self.start_order):
            rt = self.services[alias]
            if rt.process is not None and rt.process.poll() is None:
                self.console.print(f"  Stopping [bold]{rt.info.name}[/bold] (PID {rt.process.pid})...")
                rt.process.terminate()
                try:
                    rt.process.wait(timeout=SHUTDOWN_TIMEOUT)
                except subprocess.TimeoutExpired:
                    self.console.print(f"  [red]Force-killing {rt.info.name}[/red]")
                    rt.process.kill()
                    rt.process.wait(timeout=5)
                rt.state = ServiceState.STOPPED
            if rt.log_file_handle is not None:
                try:
                    rt.log_file_handle.close()
                except OSError:
                    pass
                rt.log_file_handle = None
        self.console.print("[green]All services stopped.[/green]")

    def run(self):
        """Start all requested services and enter the main loop."""
        self.running = True
        self.console.print()

        for alias in self.start_order:
            rt = self.services[alias]
            self.console.print(f"  Starting [bold]{rt.info.name}[/bold]...")

            if not self._start_service(alias):
                self.console.print(f"  [red]Failed to start {rt.info.name}![/red]")
                self._shutdown_all()
                sys.exit(1)

            wait = STARTUP_DELAY_DEPENDENCY if rt.info.depends_on else STARTUP_DELAY_DEFAULT
            time.sleep(wait)

            if rt.process and rt.process.poll() is not None:
                rt.exit_code = rt.process.returncode
                rt.state = ServiceState.CRASHED
                self.console.print(f"  [red]{rt.info.name} exited (code {rt.exit_code})[/red]")
                if rt.log_buffer:
                    for line in list(rt.log_buffer)[-10:]:
                        self.console.print(f"    [dim]{line}[/dim]")
                self._shutdown_all()
                sys.exit(1)

        self.console.print()
        self.console.print("[green bold]All services started.[/green bold]")
        self.console.print("[dim]Streaming logs... (Ctrl+C to stop)[/dim]\n")

        if self.log_to_files:
            self._save_state()

        try:
            while self.running and not self._shutdown_event.is_set():
                self._check_processes()
                crashed = [a for a, rt in self.services.items() if rt.state == ServiceState.CRASHED]
                if crashed:
                    self.console.print(
                        f"\n[red bold]Crashed: {', '.join(crashed)}. Shutting down.[/red bold]"
                    )
                    break
                time.sleep(1 / REFRESH_RATE)
        except KeyboardInterrupt:
            pass
        finally:
            self._shutdown_all()


# ---------------------------------------------------------------------------
# Background: kill, info, launch
# ---------------------------------------------------------------------------
def _load_state() -> Optional[Dict]:
    if not STATE_FILE.exists():
        return None
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def kill_background_processes(console: Optional[Console] = None) -> bool:
    """Terminate all background processes."""
    c = console or Console()
    state = _load_state()
    if not state:
        c.print("[yellow]No background orchestrator running.[/yellow]")
        return False

    killed_any = False
    orch_pid = state.get("orchestrator_pid")
    services = state.get("services", {})

    for alias, pid in services.items():
        if pid and _send_signal(pid, signal.SIGTERM):
            c.print(f"  Stopped [bold]{alias}[/bold] (PID {pid})")
            killed_any = True
            time.sleep(0.5)

    if orch_pid and _send_signal(orch_pid, signal.SIGTERM):
        c.print(f"  Stopped [bold]orchestrator[/bold] (PID {orch_pid})")
        killed_any = True

    if killed_any:
        time.sleep(1)
        for alias, pid in services.items():
            if pid and _process_exists(pid):
                _send_signal(pid, signal.SIGKILL)
                c.print(f"  Force-killed [bold]{alias}[/bold] (PID {pid})")
        if orch_pid and _process_exists(orch_pid):
            _send_signal(orch_pid, signal.SIGKILL)
            c.print(f"  Force-killed [bold]orchestrator[/bold] (PID {orch_pid})")

    try:
        if STATE_FILE.exists():
            STATE_FILE.unlink()
    except OSError:
        pass

    if killed_any:
        c.print("[green]All background processes stopped.[/green]")
    return killed_any


def _send_signal(pid: int, sig: int) -> bool:
    try:
        os.kill(pid, sig)
        return True
    except (ProcessLookupError, PermissionError):
        return False


def _process_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def show_running_processes(console: Optional[Console] = None) -> None:
    c = console or Console()
    state = _load_state()
    if not state:
        c.print("[yellow]No background orchestrator running.[/yellow]")
        c.print("[dim]Use --background to start.[/dim]")
        return

    table = Table(
        title="Nord City Background Processes",
        show_header=True,
        header_style="bold cyan",
        padding=(0, 1),
    )
    table.add_column("Process", style="bold", min_width=14)
    table.add_column("PID", width=8, justify="right")
    table.add_column("Status", width=12, justify="center")
    table.add_column("Info", min_width=20)

    orch_pid = state.get("orchestrator_pid")
    services = state.get("services", {})
    started_at = state.get("started_at", "-")

    if orch_pid:
        status = "[green]RUNNING[/green]" if _process_exists(orch_pid) else "[red]STOPPED[/red]"
        table.add_row("orchestrator", str(orch_pid), status, f"Started: {started_at[:19]}")

    for alias, pid in services.items():
        if pid:
            info = SERVICES.get(alias)
            desc = info.name if info else alias
            status = "[green]RUNNING[/green]" if _process_exists(pid) else "[red]STOPPED[/red]"
            table.add_row(alias, str(pid), status, desc)

    c.print()
    c.print(table)
    c.print()
    c.print(f"[dim]Logs: {LOGS_DIR}[/dim]")


def launch_background(
    requested: List[str],
    env_file: Path,
    console: Optional[Console] = None,
) -> None:
    """Launch orchestrator in background with logs in logs/."""
    c = console or Console()
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    orch_log = LOGS_DIR / "orchestrator.log"

    argv = [
        sys.executable,
        str(PROJECT_ROOT / "orchestrator.py"),
        "--services", ",".join(requested),
        "--background-child",
    ]
    if str(env_file) != str(PROJECT_ROOT / ".env"):
        argv.extend(["--env-file", str(env_file)])

    with open(orch_log, "a", encoding="utf-8") as logf:
        proc = subprocess.Popen(
            argv,
            cwd=str(PROJECT_ROOT),
            stdout=logf,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )

    try:
        state_data = {
            "orchestrator_pid": proc.pid,
            "services": {},
            "started_at": datetime.now().isoformat(),
        }
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state_data, f, indent=2)
    except OSError:
        pass

    c.print("[green]Orchestrator started in background.[/green]")
    c.print(f"  PID: {proc.pid}")
    c.print(f"  Logs: {LOGS_DIR}")
    c.print(f"  Orchestrator log: {orch_log}")
    c.print()
    c.print("[dim]Use --info to see processes, --kill to stop.[/dim]")


# ---------------------------------------------------------------------------
# Single-service runner
# ---------------------------------------------------------------------------
def run_single_service(alias: str, env_file: Optional[Path] = None):
    """Start a single service in foreground."""
    if alias not in SERVICES:
        print(f"Unknown service: '{alias}'", file=sys.stderr)
        sys.exit(1)

    env_path = env_file or (PROJECT_ROOT / ".env")
    if env_path.exists():
        load_dotenv(env_path, override=True)
    _update_ports_from_env()

    info = SERVICES[alias]
    console = Console()
    console.print(f"[bold]Starting {info.name}...[/bold]")
    if info.port:
        console.print(f"[dim]Port: {info.port}[/dim]")
    console.print(f"[dim]Working dir: {info.working_dir}[/dim]")
    console.print()

    if alias == "site":
        os.chdir(info.working_dir)
        os.execvp("npm", ["npm", "start"])
    else:
        os.environ["PYTHONPATH"] = str(INFRASTRUCTURE_ROOT)
        os.environ["PYTHONUNBUFFERED"] = "1"
        os.chdir(info.working_dir)
        sys.path.insert(0, str(info.working_dir))
        os.execvp(sys.executable, [sys.executable] + info.command[1:])


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="orchestrator",
        description="Nord City Orchestrator — manage all services",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Services:
  db    — Database Service   (port 8001)
  web   — Web Service       (port 8003)
  bot   — Bot Service       (port 8002)
  media — Media Service     (port 8004)
  site  — Next.js Frontend  (port 3000)

Examples:
  python orchestrator.py                    # all services, stream logs
  python orchestrator.py --services db,web,site
  python orchestrator.py --service db      # single service, foreground
  python orchestrator.py --background     # background, logs in logs/
  python orchestrator.py --kill
  python orchestrator.py --info
  python orchestrator.py --list
""",
    )
    parser.add_argument(
        "--services", "-s",
        type=str,
        default=None,
        metavar="ALIASES",
        help="Comma-separated aliases (e.g. db,web,site). Dependencies auto-included.",
    )
    parser.add_argument(
        "--service",
        type=str,
        default=None,
        metavar="ALIAS",
        help="Start a SINGLE service in foreground.",
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List available services.",
    )
    parser.add_argument(
        "--background", "-b",
        action="store_true",
        help="Run in background. Logs written to logs/.",
    )
    parser.add_argument(
        "--kill", "-k",
        action="store_true",
        help="Stop all background processes.",
    )
    parser.add_argument(
        "--info", "-i",
        action="store_true",
        help="Show running background processes.",
    )
    parser.add_argument(
        "--background-child",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--env-file",
        type=str,
        default=None,
        metavar="PATH",
        help="Path to .env (default: project root .env).",
    )
    return parser


def main():
    parser = _build_parser()
    args = parser.parse_args()
    console = Console()

    if args.kill:
        console.print("[bold]Stopping background processes...[/bold]")
        kill_background_processes(console)
        return

    if args.info:
        show_running_processes(console)
        return

    if args.list:
        table = Table(
            title="Available Services",
            show_header=True,
            header_style="bold cyan",
            padding=(0, 1),
        )
        table.add_column("Alias", width=6, style="bold")
        table.add_column("Name", min_width=18)
        table.add_column("Description")
        table.add_column("Port", width=6, justify="right")
        table.add_column("Depends On", width=20)

        for info in SERVICES.values():
            table.add_row(
                info.alias,
                info.name,
                info.description,
                str(info.port) if info.port else "-",
                ", ".join(info.depends_on) if info.depends_on else "-",
            )
        console.print(table)
        return

    if args.service:
        env_file = Path(args.env_file) if args.env_file else None
        run_single_service(args.service, env_file)
        return

    if args.services:
        requested = [s.strip() for s in args.services.split(",")]
        for s in requested:
            if s not in SERVICES:
                console.print(f"[red]Unknown service: '{s}'. Use --list.[/red]")
                sys.exit(1)
    else:
        requested = list(SERVICES.keys())

    env_file = Path(args.env_file) if args.env_file else (PROJECT_ROOT / ".env")

    if args.background:
        launch_background(requested, env_file, console)
        return

    is_background_child = args.background_child

    if not is_background_child:
        console.print()
        console.print(
            Panel(
                "[bold white]Nord City Orchestrator[/bold white]\n"
                f"[dim]Services: {', '.join(requested)}[/dim]",
                border_style="blue",
                padding=(1, 4),
            )
        )

    stream_logs = not is_background_child
    log_to_files = is_background_child

    orch = Orchestrator(
        requested,
        env_file,
        stream_logs=stream_logs,
        log_to_files=log_to_files,
        log_dir=LOGS_DIR if log_to_files else None,
    )

    def _handle_signal(signum, frame):
        orch._shutdown_event.set()
        orch.running = False

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    orch.run()


if __name__ == "__main__":
    main()
