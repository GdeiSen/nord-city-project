#!/usr/bin/env python3
"""
Nord City Services Orchestrator
================================
Manages the lifecycle of all Nord City Python microservices from a single
entry point.  Each service runs in its own subprocess; the orchestrator
monitors their health and displays a live rich-console dashboard.

Usage
-----
    python orchestrator.py                          # start ALL services with dashboard
    python orchestrator.py --services db,web        # start selected services with dashboard
    python orchestrator.py --services bot           # bot + its dependency (db)
    python orchestrator.py --service db             # start a SINGLE service (no dashboard)
    python orchestrator.py --no-dashboard           # start ALL services, stream logs to terminal
    python orchestrator.py --background             # run all services in background, logs → infrastructure/logs/
    python orchestrator.py --kill                   # stop all running background processes
    python orchestrator.py --info                   # show all running background processes
    python orchestrator.py --list                   # list available services
    python orchestrator.py --help                   # full help

Services
--------
    db    — Database Service   (FastAPI HTTP RPC, port 8001)
    web   — Web Service        (FastAPI REST API, port 8003)
    bot   — Bot Service        (Telegram bot, port 8002)
    media — Media Service      (file storage & serving, port 8004)

Notes
-----
* PostgreSQL and the Next.js frontend are NOT managed by this orchestrator.
  They must be started separately.
* A single venv and a single .env (infrastructure/.env) are used for all
  services.
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
# Path setup — make sure infrastructure root is importable
# ---------------------------------------------------------------------------
INFRASTRUCTURE_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(INFRASTRUCTURE_ROOT))

from dotenv import load_dotenv  # noqa: E402

try:
    from rich.console import Console
    from rich.live import Live
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
except ImportError:
    print(
        "ERROR: 'rich' package is required for the orchestrator.\n"
        "Install it:  pip install rich>=13.7.0",
        file=sys.stderr,
    )
    sys.exit(1)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
STARTUP_DELAY_DEPENDENCY = 3  # seconds to wait after a dependency starts
STARTUP_DELAY_DEFAULT = 1     # seconds between independent services
SHUTDOWN_TIMEOUT = 5          # seconds to wait for graceful termination
LOG_BUFFER_SIZE = 120         # last N log lines kept per service
REFRESH_RATE = 2              # dashboard refreshes per second

LOGS_DIR = INFRASTRUCTURE_ROOT / "logs"
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
    log_file_handle: Optional[object] = None  # file handle when log_to_files


# Registry — order matters (used as default start order)
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
}

ALL_ALIASES = list(SERVICES.keys())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _resolve_start_order(requested: List[str]) -> List[str]:
    """
    Topological sort: include transitive dependencies not already requested,
    then order so that dependencies come first.
    """
    needed: set[str] = set()

    def _collect(alias: str):
        if alias in needed:
            return
        needed.add(alias)
        for dep in SERVICES[alias].depends_on:
            _collect(dep)

    for alias in requested:
        _collect(alias)

    # Stable topological order that respects SERVICES insertion order
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
    db_port = os.getenv("DATABASE_SERVICE_PORT")
    if db_port:
        SERVICES["db"].port = int(db_port)
        SERVICES["db"].health_url = f"http://127.0.0.1:{db_port}/health"

    web_port = os.getenv("WEB_SERVICE_PORT")
    if web_port:
        SERVICES["web"].port = int(web_port)
        SERVICES["web"].health_url = f"http://127.0.0.1:{web_port}/health"

    bot_port = os.getenv("BOT_SERVICE_PORT")
    if bot_port:
        SERVICES["bot"].port = int(bot_port)
        SERVICES["bot"].health_url = f"http://127.0.0.1:{bot_port}/health"

    media_port = os.getenv("MEDIA_SERVICE_PORT")
    if media_port:
        SERVICES["media"].port = int(media_port)
        SERVICES["media"].health_url = f"http://127.0.0.1:{media_port}/health"


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------
class Orchestrator:
    """
    Manages service processes, streams their logs, and optionally presents a
    live rich-console dashboard.
    """

    def __init__(
        self,
        services_to_start: List[str],
        env_file: Path,
        use_dashboard: bool = True,
        stream_logs: bool = False,
        log_to_files: bool = False,
        log_dir: Optional[Path] = None,
    ):
        self.console = Console()
        self.running = False
        self._shutdown_event = threading.Event()
        self.use_dashboard = use_dashboard
        self.stream_logs = stream_logs
        self.log_to_files = log_to_files
        self.log_dir = log_dir or LOGS_DIR

        # Load .env
        if env_file.exists():
            load_dotenv(env_file, override=True)
            self.console.print(f"[dim]Loaded environment from {env_file}[/dim]")
        else:
            self.console.print(f"[yellow]Warning: .env file not found at {env_file}[/yellow]")

        _update_ports_from_env()

        # Prepare child-process environment
        self.child_env = os.environ.copy()
        self.child_env["PYTHONPATH"] = str(INFRASTRUCTURE_ROOT)
        self.child_env["PYTHONUNBUFFERED"] = "1"

        # Resolve start order (auto-includes dependencies)
        self.start_order = _resolve_start_order(services_to_start)

        # Inform about auto-included dependencies
        auto_added = set(self.start_order) - set(services_to_start)
        if auto_added:
            names = ", ".join(auto_added)
            self.console.print(
                f"[cyan]Auto-including dependencies: {names}[/cyan]"
            )

        # Create runtime entries
        self.services: Dict[str, ServiceRuntime] = {}
        for alias in self.start_order:
            self.services[alias] = ServiceRuntime(info=SERVICES[alias])

    # -- Process management --------------------------------------------------

    def _read_output(self, runtime: ServiceRuntime, alias: str):
        """Background thread: read stdout line-by-line and buffer."""
        proc = runtime.process
        if proc is None or proc.stdout is None:
            return
        try:
            for raw_line in iter(proc.stdout.readline, b""):
                text = raw_line.decode("utf-8", errors="replace").rstrip()
                if text:
                    runtime.log_buffer.append(text)
                    # Optionally stream logs directly to the terminal
                    if self.stream_logs:
                        # Simple prefixed output without extra rich styling
                        self.console.print(f"[{alias}] {text}")
        except (OSError, ValueError):
            pass  # pipe closed

    def _start_service(self, alias: str) -> bool:
        """Launch a single service subprocess."""
        rt = self.services[alias]
        rt.state = ServiceState.STARTING

        if not rt.info.working_dir.exists():
            rt.state = ServiceState.CRASHED
            rt.log_buffer.append(
                f"ERROR: working directory does not exist: {rt.info.working_dir}"
            )
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
        """Poll every process and update state if it exited."""
        for rt in self.services.values():
            if rt.process is not None and rt.state == ServiceState.RUNNING:
                rc = rt.process.poll()
                if rc is not None:
                    rt.exit_code = rc
                    rt.state = (
                        ServiceState.CRASHED if rc != 0 else ServiceState.STOPPED
                    )

    def _save_state(self):
        """Save orchestrator and service PIDs to state file for --kill/--info."""
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
            self.console.print(f"[yellow]Warning: could not save state file: {e}[/yellow]")

    def _remove_state(self):
        """Remove state file on shutdown."""
        try:
            if STATE_FILE.exists():
                STATE_FILE.unlink()
        except OSError:
            pass

    def _shutdown_all(self):
        """Gracefully terminate all running processes (reverse order)."""
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

    # -- Dashboard -----------------------------------------------------------

    def _build_dashboard(self) -> Panel:
        """Build the rich dashboard panel."""
        # -- Status table --
        table = Table(
            show_header=True,
            header_style="bold cyan",
            expand=True,
            padding=(0, 1),
        )
        table.add_column("Service", style="bold", min_width=18)
        table.add_column("Alias", width=6, justify="center")
        table.add_column("Status", width=14, justify="center")
        table.add_column("PID", width=8, justify="right")
        table.add_column("Port", width=6, justify="right")
        table.add_column("Uptime", width=10, justify="right")

        for alias in self.start_order:
            rt = self.services[alias]
            style, icon, label = STATE_DISPLAY[rt.state]
            status_text = Text(f"{icon} {label}", style=style)

            pid = str(rt.process.pid) if rt.process and rt.process.pid else "-"
            port_str = str(rt.info.port) if rt.info.port else "-"
            uptime = _format_uptime(rt.started_at) if rt.state == ServiceState.RUNNING else "-"

            table.add_row(rt.info.name, alias, status_text, pid, port_str, uptime)

        # -- Recent logs --
        log_lines: List[Text] = []
        for alias in self.start_order:
            rt = self.services[alias]
            if rt.log_buffer:
                # Show last 3 lines per service
                recent = list(rt.log_buffer)[-3:]
                for line in recent:
                    style, _, _ = STATE_DISPLAY[rt.state]
                    prefix = Text(f"[{alias:>3s}] ", style="bold " + style)
                    content = Text(line[:200], style="dim")
                    full = prefix + content
                    log_lines.append(full)

        # Build final layout
        from rich.console import Group
        parts = [table]
        if log_lines:
            parts.append(Text(""))  # spacer
            parts.append(Text("Recent logs:", style="bold underline"))
            parts.extend(log_lines[-15:])  # last 15 total lines

        return Panel(
            Group(*parts),
            title="[bold white]Nord City Orchestrator[/bold white]",
            subtitle="[dim]Ctrl+C to stop all services[/dim]",
            border_style="blue",
            padding=(1, 2),
        )

    # -- Main loop -----------------------------------------------------------

    def run(self):
        """Start all requested services and enter the main loop."""
        self.running = True
        self.console.print()

        # Start services in topological order
        for alias in self.start_order:
            rt = self.services[alias]
            self.console.print(f"  Starting [bold]{rt.info.name}[/bold]...")

            if not self._start_service(alias):
                self.console.print(f"  [red]Failed to start {rt.info.name}![/red]")
                self._shutdown_all()
                sys.exit(1)

            # Delay to let the service initialise before dependents start
            wait = STARTUP_DELAY_DEPENDENCY if rt.info.depends_on else STARTUP_DELAY_DEFAULT
            time.sleep(wait)

            # Verify it hasn't immediately crashed
            if rt.process and rt.process.poll() is not None:
                rt.exit_code = rt.process.returncode
                rt.state = ServiceState.CRASHED
                self.console.print(
                    f"  [red]{rt.info.name} exited immediately "
                    f"(code {rt.exit_code})[/red]"
                )
                # Show captured output
                if rt.log_buffer:
                    for line in list(rt.log_buffer)[-10:]:
                        self.console.print(f"    [dim]{line}[/dim]")
                self._shutdown_all()
                sys.exit(1)

        self.console.print()
        self.console.print("[green bold]All services started successfully.[/green bold]")
        self.console.print()

        # Save state file when running in background (for --kill and --info)
        if self.log_to_files:
            self._save_state()

        # Choose between dashboard mode and plain log-streaming mode
        try:
            if self.use_dashboard:
                # Enter live dashboard
                with Live(
                    self._build_dashboard(),
                    console=self.console,
                    refresh_per_second=REFRESH_RATE,
                    transient=False,
                ) as live:
                    while self.running and not self._shutdown_event.is_set():
                        self._check_processes()
                        live.update(self._build_dashboard())

                        # If any critical service crashed, stop everything
                        crashed = [
                            a for a, rt in self.services.items()
                            if rt.state == ServiceState.CRASHED
                        ]
                        if crashed:
                            self.console.print(
                                f"\n[red bold]Service(s) crashed: "
                                f"{', '.join(crashed)}. Shutting down.[/red bold]"
                            )
                            break

                        time.sleep(1 / REFRESH_RATE)
            else:
                # Simple loop: periodically check processes; log lines are streamed
                # directly from reader threads via self.stream_logs.
                self.console.print(
                    "[dim]Dashboard disabled; streaming logs from all services...[/dim]"
                )
                while self.running and not self._shutdown_event.is_set():
                    self._check_processes()

                    crashed = [
                        a for a, rt in self.services.items()
                        if rt.state == ServiceState.CRASHED
                    ]
                    if crashed:
                        self.console.print(
                            f"\n[red bold]Service(s) crashed: "
                            f"{', '.join(crashed)}. Shutting down.[/red bold]"
                        )
                        break

                    time.sleep(1 / REFRESH_RATE)
        except KeyboardInterrupt:
            pass
        finally:
            self._shutdown_all()


# ---------------------------------------------------------------------------
# Background mode: kill, info, launch
# ---------------------------------------------------------------------------
def _load_state() -> Optional[Dict]:
    """Load state from file. Returns None if not found or invalid."""
    if not STATE_FILE.exists():
        return None
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def kill_background_processes(console: Optional[Console] = None) -> bool:
    """
    Find and terminate all background orchestrator processes and their services.
    Returns True if any processes were killed, False otherwise.
    """
    c = console or Console()
    state = _load_state()
    if not state:
        c.print("[yellow]No background orchestrator is running.[/yellow]")
        return False

    killed_any = False
    orch_pid = state.get("orchestrator_pid")
    services = state.get("services", {})

    # Kill service processes first (children), then orchestrator
    for alias, pid in services.items():
        if pid and _send_signal(pid, signal.SIGTERM):
            c.print(f"  Stopped [bold]{alias}[/bold] (PID {pid})")
            killed_any = True
            time.sleep(0.5)  # brief pause between kills

    if orch_pid and _send_signal(orch_pid, signal.SIGTERM):
        c.print(f"  Stopped [bold]orchestrator[/bold] (PID {orch_pid})")
        killed_any = True

    if killed_any:
        time.sleep(1)  # allow graceful shutdown
        # Force kill any remaining
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
    """Send signal to process. Returns True if process existed."""
    try:
        os.kill(pid, sig)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return False


def _process_exists(pid: int) -> bool:
    """Check if process with given PID exists."""
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # exists but we can't signal it


def show_running_processes(console: Optional[Console] = None) -> None:
    """Display all running background processes from state file."""
    c = console or Console()
    state = _load_state()
    if not state:
        c.print("[yellow]No background orchestrator is running.[/yellow]")
        c.print("[dim]Use --background to start services in the background.[/dim]")
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
    c.print(f"[dim]Logs directory: {LOGS_DIR}[/dim]")


def launch_background(
    requested: List[str],
    env_file: Path,
    console: Optional[Console] = None,
) -> None:
    """
    Launch orchestrator in background with logs written to infrastructure/logs.
    """
    c = console or Console()
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    orch_log = LOGS_DIR / "orchestrator.log"

    argv = [
        sys.executable,
        str(INFRASTRUCTURE_ROOT / "orchestrator.py"),
        "--services", ",".join(requested),
        "--background-child",
    ]
    if str(env_file) != str(INFRASTRUCTURE_ROOT / ".env"):
        argv.extend(["--env-file", str(env_file)])

    with open(orch_log, "a", encoding="utf-8") as logf:
        proc = subprocess.Popen(
            argv,
            cwd=str(INFRASTRUCTURE_ROOT),
            stdout=logf,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )

    # Write initial state so --kill/--info work before services are fully started
    try:
        state_data = {
            "orchestrator_pid": proc.pid,
            "services": {},
            "started_at": datetime.now().isoformat(),
        }
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state_data, f, indent=2)
    except OSError:
        pass

    c.print("[green]Orchestrator started in background.[/green]")
    c.print(f"  PID: {proc.pid}")
    c.print(f"  Logs: {LOGS_DIR}")
    c.print(f"  Orchestrator log: {orch_log}")
    c.print()
    c.print("[dim]Use --info to see running processes, --kill to stop all.[/dim]")


# ---------------------------------------------------------------------------
# Single-service runner (no dashboard)
# ---------------------------------------------------------------------------
def run_single_service(alias: str, env_file: Optional[Path] = None):
    """
    Start a single service in the foreground (no dashboard, no subprocess).

    Useful for development / debugging when you want direct stdio from
    one service.

    Parameters
    ----------
    alias : str
        Service alias ('db', 'web', 'bot').
    env_file : Path, optional
        Path to .env file.  Defaults to infrastructure/.env.
    """
    if alias not in SERVICES:
        print(f"Unknown service: '{alias}'", file=sys.stderr)
        sys.exit(1)

    env_path = env_file or (INFRASTRUCTURE_ROOT / ".env")
    if env_path.exists():
        load_dotenv(env_path, override=True)
    _update_ports_from_env()

    os.environ["PYTHONPATH"] = str(INFRASTRUCTURE_ROOT)
    os.environ["PYTHONUNBUFFERED"] = "1"

    info = SERVICES[alias]
    console = Console()
    console.print(f"[bold]Starting {info.name} in foreground mode...[/bold]")
    if info.port:
        console.print(f"[dim]Port: {info.port}[/dim]")
    console.print(f"[dim]Working dir: {info.working_dir}[/dim]")
    console.print()

    os.chdir(info.working_dir)
    sys.path.insert(0, str(info.working_dir))

    # Execute directly (replaces current process)
    os.execvp(sys.executable, [sys.executable] + info.command[1:])


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="orchestrator",
        description="Nord City Services Orchestrator — manage all Python microservices",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Available services:
  db   — Database Service   (FastAPI HTTP RPC, port 8001)
  web  — Web Service        (FastAPI REST API, port 8003)
  bot  — Bot Service        (Telegram bot)

Examples:
  python orchestrator.py                          # start all services
  python orchestrator.py --services db,web        # only database + web
  python orchestrator.py --services bot           # bot (auto-includes db)
  python orchestrator.py --service db             # single service, foreground
  python orchestrator.py --background            # run in background, logs in infrastructure/logs/
  python orchestrator.py --kill                  # stop all background processes
  python orchestrator.py --info                  # show running background processes
  python orchestrator.py --list                   # show service table
""",
    )
    parser.add_argument(
        "--services", "-s",
        type=str,
        default=None,
        metavar="ALIASES",
        help="Comma-separated service aliases to start (e.g. db,web,bot). "
             "Dependencies are auto-included.",
    )
    parser.add_argument(
        "--service",
        type=str,
        default=None,
        metavar="ALIAS",
        help="Start a SINGLE service in foreground mode (no dashboard, direct stdio). "
             "Useful for development/debugging.",
    )
    parser.add_argument(
        "--no-dashboard",
        action="store_true",
        help=(
            "Disable the rich dashboard and stream logs from all started services "
            "directly to the terminal."
        ),
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List available services and exit.",
    )
    parser.add_argument(
        "--background", "-b",
        action="store_true",
        help="Run orchestrator and all services in background. Logs are written to infrastructure/logs/.",
    )
    parser.add_argument(
        "--kill", "-k",
        action="store_true",
        help="Stop all running background processes (orchestrator and services). Does not start new services.",
    )
    parser.add_argument(
        "--info", "-i",
        action="store_true",
        help="Show all running background processes and their status.",
    )
    parser.add_argument(
        "--background-child",
        action="store_true",
        help=argparse.SUPPRESS,  # Internal: used when running as background child
    )
    parser.add_argument(
        "--env-file",
        type=str,
        default=None,
        metavar="PATH",
        help="Path to .env file (default: infrastructure/.env).",
    )
    return parser


def main():
    parser = _build_parser()
    args = parser.parse_args()
    console = Console()

    # ── --kill ───────────────────────────────────────────────────────────
    if args.kill:
        console.print("[bold]Stopping background processes...[/bold]")
        kill_background_processes(console)
        return

    # ── --info ───────────────────────────────────────────────────────────
    if args.info:
        show_running_processes(console)
        return

    # ── --list ──────────────────────────────────────────────────────────
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
        table.add_column("Depends On", width=12)

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

    # ── --service (single, foreground) ──────────────────────────────────
    if args.service:
        env_file = Path(args.env_file) if args.env_file else None
        run_single_service(args.service, env_file)
        return  # unreachable — execvp replaces process

    # ── --services / default (orchestrator run) ─────────────────────────
    if args.services:
        requested = [s.strip() for s in args.services.split(",")]
        for s in requested:
            if s not in SERVICES:
                console.print(
                    f"[red]Unknown service: '{s}'. "
                    f"Use --list to see available services.[/red]"
                )
                sys.exit(1)
    else:
        requested = list(SERVICES.keys())

    env_file = Path(args.env_file) if args.env_file else (INFRASTRUCTURE_ROOT / ".env")

    # ── --background ───────────────────────────────────────────────────
    if args.background:
        launch_background(requested, env_file, console)
        return

    # ── --background-child (internal) ───────────────────────────────────
    is_background_child = args.background_child

    # Banner (skip for background child - logs go to file)
    if not is_background_child:
        console.print()
        console.print(
            Panel(
                "[bold white]Nord City Services Orchestrator[/bold white]\n"
                f"[dim]Services: {', '.join(requested)}[/dim]",
                border_style="blue",
                padding=(1, 4),
            )
        )

    use_dashboard = not args.no_dashboard and not is_background_child
    stream_logs = args.no_dashboard and not is_background_child
    log_to_files = is_background_child

    orch = Orchestrator(
        requested,
        env_file,
        use_dashboard=use_dashboard,
        stream_logs=stream_logs,
        log_to_files=log_to_files,
        log_dir=LOGS_DIR if log_to_files else None,
    )

    # Signal handlers
    def _handle_signal(signum, frame):
        orch._shutdown_event.set()
        orch.running = False

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    orch.run()


if __name__ == "__main__":
    main()
