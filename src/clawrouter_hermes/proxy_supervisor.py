"""Detect / lazily spawn / heartbeat the local ``npx @blockrun/clawrouter`` proxy.

Design notes:
- ``register(ctx)`` only *probes* the proxy; it never spawns at startup so
  Hermes' plugin discovery stays non-blocking.
- ``ensure_running()`` is called by tool handlers and CLI subcommands on
  first use. It probes, then spawns the proxy if the port is free, falling
  through to 8403–8410 on collision. When ``setup`` has pre-installed the
  proxy into ``~/.openclaw/npm`` it launches that binary directly (zero
  download/link latency); otherwise it falls back to ``npx -y
  @blockrun/clawrouter --port <port>``.
- A background heartbeat thread restarts the subprocess on death (capped
  at 3 restarts per minute).
- ``CLAWROUTER_PROXY_URL`` skips supervision entirely (service-managed
  proxies).
- ``HERMES_CLAWROUTER_AUTOSPAWN=0`` forces "manual start required" mode.
"""

from __future__ import annotations

import logging
import os
import shutil
import socket
import subprocess
import threading
import time
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version as _pkg_version
from typing import Optional

import httpx

from . import state

logger = logging.getLogger(__name__)

try:
    _PLUGIN_VERSION = _pkg_version("hermes-plugin-clawrouter")
except PackageNotFoundError:  # source checkout without installed dist metadata
    _PLUGIN_VERSION = "0"

# Folded into the proxy's outbound User-Agent (it reads CLAWROUTER_CLIENT) so
# BlockRun can attribute traffic to Hermes: `clawrouter/<v> hermes-plugin/<v>`.
_CLIENT_TAG = f"hermes-plugin/{_PLUGIN_VERSION}"

_PROBE_TIMEOUT_S = 0.5
_SPAWN_TIMEOUT_S = 30.0
_HEARTBEAT_INTERVAL_S = 5.0
_RESTART_WINDOW_S = 60.0
_MAX_RESTARTS_PER_WINDOW = 3
_PORT_SCAN_RANGE = range(8402, 8411)

_lock = threading.Lock()
_process: Optional[subprocess.Popen] = None
_heartbeat: Optional[threading.Thread] = None
_restart_times: list[float] = []
_supervised_port: Optional[int] = None
_stop_event = threading.Event()


@dataclass
class ProxyStatus:
    reachable: bool
    base_url: str
    port: int
    pid: Optional[int]
    managed: bool  # we spawned it vs. an external instance reused
    error: Optional[str] = None


def _probe(base_url: str, timeout: float = _PROBE_TIMEOUT_S) -> bool:
    try:
        resp = httpx.get(f"{base_url}/models", timeout=timeout)
    except httpx.HTTPError:
        return False
    return resp.status_code == 200


def _port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def _claim_port() -> int:
    for port in _PORT_SCAN_RANGE:
        base = f"http://127.0.0.1:{port}/v1"
        if _probe(base):
            return port
        if _port_free(port):
            return port
    raise RuntimeError(
        f"No free port in {_PORT_SCAN_RANGE.start}-{_PORT_SCAN_RANGE.stop - 1} "
        f"and no reachable ClawRouter proxy on those ports."
    )


def _node_available() -> bool:
    return shutil.which("npx") is not None


def _build_env() -> dict:
    env = dict(os.environ)
    env.setdefault("CLAWROUTER_ROUTING_PROFILE", state.get_profile())
    # Tag the proxy's User-Agent as Hermes-originated. setdefault so an explicit
    # user-set CLAWROUTER_CLIENT wins.
    env.setdefault("CLAWROUTER_CLIENT", _CLIENT_TAG)
    return env


def _local_proxy_bin() -> Optional[str]:
    """Path to the proxy binary pre-installed by ``setup`` into
    ``~/.openclaw/npm`` (see ``cli._install_clawrouter_proxy``), if present.

    Invoking it directly skips ``npx``'s resolve/link-into-``_npx`` step, so a
    warm pre-install gives a genuinely zero-download, zero-link first launch.
    """
    bin_path = (
        state.STATE_DIR / "npm" / "node_modules" / ".bin" / "clawrouter"
    )
    return str(bin_path) if bin_path.is_file() else None


def _spawn_cmd(port: int) -> tuple[list[str], Optional[str]]:
    """Return ``(argv, cwd)`` for launching the proxy.

    Prefer the pre-installed binary in ``~/.openclaw/npm`` (no download/link
    latency); fall back to ``npx -y`` which resolves/installs on demand.
    """
    local = _local_proxy_bin()
    if local is not None:
        # cwd at the npm root so the bin shim resolves its own deps cleanly.
        return [local, "--port", str(port)], str(state.STATE_DIR / "npm")
    return ["npx", "-y", "@blockrun/clawrouter", "--port", str(port)], None


def _spawn(port: int) -> subprocess.Popen:
    cmd, cwd = _spawn_cmd(port)
    logger.info("Spawning ClawRouter proxy: %s", " ".join(cmd))
    return subprocess.Popen(
        cmd,
        cwd=cwd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        env=_build_env(),
        start_new_session=True,
    )


def _wait_ready(base_url: str, deadline: float) -> bool:
    while time.time() < deadline:
        if _probe(base_url):
            return True
        time.sleep(0.5)
    return False


def _within_restart_budget() -> bool:
    now = time.time()
    while _restart_times and now - _restart_times[0] > _RESTART_WINDOW_S:
        _restart_times.pop(0)
    return len(_restart_times) < _MAX_RESTARTS_PER_WINDOW


def _heartbeat_loop() -> None:
    global _process
    while not _stop_event.is_set():
        time.sleep(_HEARTBEAT_INTERVAL_S)
        with _lock:
            proc = _process
            port = _supervised_port
        if proc is None or port is None:
            continue
        if proc.poll() is None:
            continue
        logger.warning("ClawRouter proxy died (pid was %s)", proc.pid)
        if not _within_restart_budget():
            logger.error(
                "ClawRouter proxy crashed %d times in %ds — giving up",
                _MAX_RESTARTS_PER_WINDOW, int(_RESTART_WINDOW_S),
            )
            with _lock:
                _process = None
            return
        try:
            with _lock:
                _process = _spawn(port)
                _restart_times.append(time.time())
        except Exception as exc:
            logger.error("Failed to restart proxy: %s", exc)
            return


def _start_heartbeat() -> None:
    global _heartbeat
    if _heartbeat is not None and _heartbeat.is_alive():
        return
    _stop_event.clear()
    _heartbeat = threading.Thread(
        target=_heartbeat_loop, name="clawrouter-heartbeat", daemon=True,
    )
    _heartbeat.start()


def ensure_running(*, autospawn: Optional[bool] = None) -> ProxyStatus:
    """Probe the proxy and spawn it lazily if needed.

    *autospawn* defaults to ``state.autospawn_enabled()`` (true unless
    ``HERMES_CLAWROUTER_AUTOSPAWN=0``).
    """
    global _process, _supervised_port

    if os.environ.get("CLAWROUTER_PROXY_URL", "").strip():
        base = state.proxy_base_url()
        return ProxyStatus(
            reachable=_probe(base),
            base_url=base,
            port=0,
            pid=None,
            managed=False,
        )

    do_spawn = state.autospawn_enabled() if autospawn is None else autospawn

    with _lock:
        port = state.get_port()
        base = f"http://127.0.0.1:{port}/v1"
        if _probe(base):
            return ProxyStatus(
                reachable=True,
                base_url=base,
                port=port,
                pid=_process.pid if _process else None,
                managed=_process is not None,
            )

        if not do_spawn:
            return ProxyStatus(
                reachable=False,
                base_url=base,
                port=port,
                pid=None,
                managed=False,
                error=(
                    "Proxy not running and HERMES_CLAWROUTER_AUTOSPAWN=0. "
                    "Start it manually: npx @blockrun/clawrouter"
                ),
            )

        if not _node_available():
            return ProxyStatus(
                reachable=False,
                base_url=base,
                port=port,
                pid=None,
                managed=False,
                error=(
                    "`npx` not found on PATH. Install Node.js 18+ from "
                    "https://nodejs.org and re-run."
                ),
            )

        try:
            port = _claim_port()
        except RuntimeError as exc:
            return ProxyStatus(
                reachable=False, base_url=base, port=port, pid=None,
                managed=False, error=str(exc),
            )

        base = f"http://127.0.0.1:{port}/v1"
        state.set_port(port)
        _supervised_port = port
        _process = _spawn(port)

    deadline = time.time() + _SPAWN_TIMEOUT_S
    if not _wait_ready(base, deadline):
        with _lock:
            if _process is not None:
                _process.terminate()
                _process = None
        return ProxyStatus(
            reachable=False, base_url=base, port=port, pid=None,
            managed=False,
            error=(
                "ClawRouter proxy spawned but never became reachable within "
                f"{int(_SPAWN_TIMEOUT_S)}s. Check `npx @blockrun/clawrouter` "
                "manually."
            ),
        )

    _start_heartbeat()
    return ProxyStatus(
        reachable=True, base_url=base, port=port,
        pid=_process.pid if _process else None,
        managed=True,
    )


def stop() -> None:
    """Tear down the supervisor — used on plugin reload / process exit."""
    global _process
    _stop_event.set()
    with _lock:
        if _process is not None and _process.poll() is None:
            try:
                _process.terminate()
            except OSError:
                pass
        _process = None


def status() -> ProxyStatus:
    """Non-spawning status check, suitable for ``doctor``."""
    base = state.proxy_base_url()
    reachable = _probe(base)
    return ProxyStatus(
        reachable=reachable,
        base_url=base,
        port=state.get_port(),
        pid=_process.pid if _process else None,
        managed=_process is not None,
    )
