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

import json
import logging
import os
import shutil
import socket
import subprocess
import threading
import time
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version as _pkg_version
from pathlib import Path
from typing import Optional

import httpx

from . import api_key, state

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

#: First @blockrun/clawrouter that understands ``BLOCKRUN_API_KEY``. Older
#: proxies ignore the key *silently* and sign x402 payments from the wallet
#: instead — a configured key would spend USDC the user thought was parked.
#: That is a money bug, not a feature gap, so we refuse to launch a stale
#: pre-installed binary while a key is configured and take the (slower) npx
#: path to a current one instead.
MIN_API_KEY_PROXY_VERSION = (0, 12, 268)

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
    #: "api-key" | "wallet" — how the *running* proxy is paying. Read from its
    #: own /health so the plugin never describes a rail the proxy isn't on.
    auth_mode: str = "wallet"
    api_key_label: Optional[str] = None
    gateway: Optional[str] = None


def desired_auth_mode() -> str:
    """The rail this machine is configured for, before any proxy is running.

    A key wins over a wallet whenever both are present — the same precedence
    the proxy itself applies, so ``doctor`` and ``setup`` can describe the
    right rail before anything has been spawned.
    """
    return "api-key" if api_key.resolve() is not None else "wallet"


def _health(root_url: str, timeout: float = _PROBE_TIMEOUT_S) -> Optional[dict]:
    """Read the proxy's own ``/health``.

    Lives at the root, not under ``/v1``. Returns ``None`` when the proxy is
    unreachable or answers with something that isn't JSON.
    """
    try:
        resp = httpx.get(f"{root_url}/health", timeout=timeout)
        if resp.status_code != 200:
            return None
        data = resp.json()
    except (httpx.HTTPError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _auth_mode_of(health: Optional[dict]) -> str:
    """Auth mode a ``/health`` payload describes.

    ClawRouter only started reporting ``authMode`` in 0.12.268; before that
    the only rail was the wallet, so an absent field means wallet.
    """
    if not health:
        return "wallet"
    return "api-key" if health.get("authMode") == "api-key" else "wallet"


def _root_of(base_url: str) -> str:
    return base_url[:-3] if base_url.endswith("/v1") else base_url


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


def _claim_port(want_mode: Optional[str] = None) -> int:
    """Find a port to use: an existing proxy we may reuse, or a free one.

    *want_mode* guards the reuse half. Two ClawRouters bill different accounts
    from different hosts, so attaching to one running on the other rail would
    spend money the caller did not mean to spend — a wallet proxy left over on
    :8402 must not silently serve a user who has since configured an API key.
    The proxy itself refuses that reuse; we have to refuse it too, because we
    reuse by probing rather than by asking it to start.
    """
    want = want_mode or desired_auth_mode()
    for port in _PORT_SCAN_RANGE:
        base = f"http://127.0.0.1:{port}/v1"
        if _probe(base):
            if _auth_mode_of(_health(_root_of(base))) == want:
                return port
            logger.info(
                "clawrouter: proxy on :%d is on the other auth rail — looking further", port
            )
            continue
        if _port_free(port):
            return port
    raise RuntimeError(
        f"No free port in {_PORT_SCAN_RANGE.start}-{_PORT_SCAN_RANGE.stop - 1} "
        f"and every reachable ClawRouter proxy there is on the other auth rail "
        f"({'API key' if want == 'api-key' else 'wallet'} was requested). "
        f"Stop one of them, or set CLAWROUTER_PROXY_URL."
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


def _npm_root() -> Path:
    return state.STATE_DIR / "npm"


def local_proxy_version() -> Optional[tuple[int, ...]]:
    """Version of the pre-installed ``@blockrun/clawrouter``, if any.

    ``None`` when nothing is installed there or the manifest is unreadable —
    callers treat that as "cannot vouch for it", which is the safe reading.
    """
    manifest = (
        _npm_root() / "node_modules" / "@blockrun" / "clawrouter" / "package.json"
    )
    try:
        raw = json.loads(manifest.read_text(encoding="utf-8")).get("version")
    except (OSError, ValueError, AttributeError):
        return None
    if not isinstance(raw, str):
        return None
    parts = raw.split("-", 1)[0].split(".")
    try:
        return tuple(int(p) for p in parts[:3])
    except ValueError:
        return None


def _local_proxy_bin() -> Optional[str]:
    """Path to the proxy binary pre-installed by ``setup`` into
    ``~/.openclaw/npm`` (see ``cli._install_clawrouter_proxy``), if present.

    Invoking it directly skips ``npx``'s resolve/link-into-``_npx`` step, so a
    warm pre-install gives a genuinely zero-download, zero-link first launch.
    """
    bin_path = _npm_root() / "node_modules" / ".bin" / "clawrouter"
    return str(bin_path) if bin_path.is_file() else None


def _spawn_cmd(port: int) -> tuple[list[str], Optional[str]]:
    """Return ``(argv, cwd)`` for launching the proxy.

    Prefer the pre-installed binary in ``~/.openclaw/npm`` (no download/link
    latency); fall back to ``npx -y`` which resolves/installs on demand.

    One exception overrides the fast path: a configured API key plus a
    pre-install older than :data:`MIN_API_KEY_PROXY_VERSION`. That proxy
    ignores the key without saying so and pays from the wallet instead, so we
    pin ``@latest`` through npx — slower, but it spends the account the user
    asked us to spend.
    """
    local = _local_proxy_bin()
    if local is not None:
        installed = local_proxy_version()
        if (
            api_key.resolve() is not None
            and (installed is None or installed < MIN_API_KEY_PROXY_VERSION)
        ):
            logger.warning(
                "clawrouter: pre-installed proxy %s predates API-key support "
                "(needs >= %s) and would pay from the wallet instead — "
                "launching @latest via npx. Run `hermes-clawrouter setup` to "
                "refresh the pre-install.",
                ".".join(str(p) for p in installed) if installed else "(unknown)",
                ".".join(str(p) for p in MIN_API_KEY_PROXY_VERSION),
            )
            return (
                ["npx", "-y", "@blockrun/clawrouter@latest", "--port", str(port)],
                None,
            )
        # cwd at the npm root so the bin shim resolves its own deps cleanly.
        return [local, "--port", str(port)], str(_npm_root())
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

    want = desired_auth_mode()

    if os.environ.get("CLAWROUTER_PROXY_URL", "").strip():
        base = state.proxy_base_url()
        reachable = _probe(base)
        health = _health(_root_of(base)) if reachable else None
        return ProxyStatus(
            reachable=reachable,
            base_url=base,
            port=0,
            pid=None,
            managed=False,
            auth_mode=_auth_mode_of(health),
            api_key_label=(health or {}).get("apiKey"),
            gateway=(health or {}).get("gateway"),
        )

    do_spawn = state.autospawn_enabled() if autospawn is None else autospawn

    with _lock:
        port = state.get_port()
        base = f"http://127.0.0.1:{port}/v1"
        mode_mismatch = False
        if _probe(base):
            health = _health(_root_of(base))
            running_mode = _auth_mode_of(health)
            if running_mode == want:
                return ProxyStatus(
                    reachable=True,
                    base_url=base,
                    port=port,
                    pid=_process.pid if _process else None,
                    managed=_process is not None,
                    auth_mode=running_mode,
                    api_key_label=(health or {}).get("apiKey"),
                    gateway=(health or {}).get("gateway"),
                )
            # Reusing it would bill the other account. Leave it alone and go
            # find a port of our own.
            mode_mismatch = True

        if not do_spawn:
            return ProxyStatus(
                reachable=False,
                base_url=base,
                port=port,
                pid=None,
                managed=False,
                auth_mode=want,
                error=(
                    f"A ClawRouter proxy is running on :{port} but it is paying "
                    f"with {'a wallet' if want == 'api-key' else 'an API key'}, not "
                    f"{'an API key' if want == 'api-key' else 'a wallet'}. "
                    "Stop it, or unset HERMES_CLAWROUTER_AUTOSPAWN=0 so a "
                    "matching one can start on another port."
                    if mode_mismatch
                    else "Proxy not running and HERMES_CLAWROUTER_AUTOSPAWN=0. "
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
                auth_mode=want,
                error=(
                    "`npx` not found on PATH. Install Node.js 18+ from "
                    "https://nodejs.org and re-run."
                ),
            )

        try:
            port = _claim_port(want)
        except RuntimeError as exc:
            return ProxyStatus(
                reachable=False, base_url=base, port=port, pid=None,
                managed=False, auth_mode=want, error=str(exc),
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
            managed=False, auth_mode=want,
            error=(
                "ClawRouter proxy spawned but never became reachable within "
                f"{int(_SPAWN_TIMEOUT_S)}s. Check `npx @blockrun/clawrouter` "
                "manually."
            ),
        )

    _start_heartbeat()
    health = _health(_root_of(base))
    return ProxyStatus(
        reachable=True, base_url=base, port=port,
        pid=_process.pid if _process else None,
        managed=True,
        auth_mode=_auth_mode_of(health),
        api_key_label=(health or {}).get("apiKey"),
        gateway=(health or {}).get("gateway"),
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
    health = _health(_root_of(base)) if reachable else None
    return ProxyStatus(
        reachable=reachable,
        base_url=base,
        port=state.get_port(),
        pid=_process.pid if _process else None,
        managed=_process is not None,
        # A running proxy's own /health is the truth; when nothing is running,
        # report the rail this machine is configured for.
        auth_mode=_auth_mode_of(health) if reachable else desired_auth_mode(),
        api_key_label=(health or {}).get("apiKey"),
        gateway=(health or {}).get("gateway"),
    )
