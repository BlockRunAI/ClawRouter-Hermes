"""proxy_supervisor.py — probing, port claiming, env overrides.

We don't actually spawn ``npx`` in tests (no Node guarantee in CI). Instead
we monkeypatch :func:`_node_available` and :func:`_spawn` to drive the
supervisor through its branches.
"""

from __future__ import annotations

import json
from unittest.mock import patch

import httpx


def test_external_proxy_url_skips_spawn(isolated_home, monkeypatch):
    from clawrouter_hermes import proxy_supervisor

    monkeypatch.setenv("CLAWROUTER_PROXY_URL", "https://example.test/v1")

    def fake_probe(base_url, timeout=0.5):
        return base_url == "https://example.test/v1"

    monkeypatch.setattr(proxy_supervisor, "_probe", fake_probe)
    status = proxy_supervisor.ensure_running()
    assert status.reachable is True
    assert status.managed is False
    assert status.base_url == "https://example.test/v1"


def test_no_node_returns_actionable_error(isolated_home, monkeypatch):
    from clawrouter_hermes import proxy_supervisor

    monkeypatch.setattr(proxy_supervisor, "_probe", lambda *_a, **_k: False)
    monkeypatch.setattr(proxy_supervisor, "_node_available", lambda: False)

    status = proxy_supervisor.ensure_running()
    assert status.reachable is False
    assert "Node" in (status.error or "")
    assert "nodejs.org" in (status.error or "")


def test_autospawn_disabled(isolated_home, monkeypatch):
    from clawrouter_hermes import proxy_supervisor

    monkeypatch.setenv("HERMES_CLAWROUTER_AUTOSPAWN", "0")
    monkeypatch.setattr(proxy_supervisor, "_probe", lambda *_a, **_k: False)

    status = proxy_supervisor.ensure_running()
    assert status.reachable is False
    assert "manually" in (status.error or "").lower()


def test_proxy_reachable_returns_managed_false(isolated_home, monkeypatch):
    from clawrouter_hermes import proxy_supervisor

    monkeypatch.setattr(proxy_supervisor, "_probe", lambda *_a, **_k: True)
    status = proxy_supervisor.ensure_running()
    assert status.reachable is True
    assert status.managed is False
    assert status.base_url.endswith("/v1")


def test_status_non_spawning(isolated_home, monkeypatch):
    from clawrouter_hermes import proxy_supervisor

    monkeypatch.setattr(proxy_supervisor, "_probe", lambda *_a, **_k: False)
    status = proxy_supervisor.status()
    assert status.reachable is False
    assert status.base_url.startswith("http://127.0.0.1:")


def test_spawn_cmd_falls_back_to_npx_when_no_local_bin(isolated_home):
    from clawrouter_hermes import proxy_supervisor

    cmd, cwd = proxy_supervisor._spawn_cmd(8402)
    assert cmd == ["npx", "-y", "@blockrun/clawrouter", "--port", "8402"]
    assert cwd is None


def test_spawn_cmd_prefers_pre_installed_bin(isolated_home):
    from clawrouter_hermes import proxy_supervisor, state

    bin_dir = state.STATE_DIR / "npm" / "node_modules" / ".bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    bin_path = bin_dir / "clawrouter"
    bin_path.write_text("#!/usr/bin/env node\n")

    cmd, cwd = proxy_supervisor._spawn_cmd(8407)
    assert cmd == [str(bin_path), "--port", "8407"]
    assert cwd == str(state.STATE_DIR / "npm")


def test_build_env_tags_user_agent_as_hermes(isolated_home, monkeypatch):
    from clawrouter_hermes import proxy_supervisor

    monkeypatch.delenv("CLAWROUTER_CLIENT", raising=False)
    env = proxy_supervisor._build_env()
    # The proxy folds this into its User-Agent → clawrouter/<v> hermes-plugin/<v>.
    assert env["CLAWROUTER_CLIENT"].startswith("hermes-plugin/")


def test_build_env_respects_explicit_client_override(isolated_home, monkeypatch):
    from clawrouter_hermes import proxy_supervisor

    monkeypatch.setenv("CLAWROUTER_CLIENT", "custom-host/9.9")
    env = proxy_supervisor._build_env()
    assert env["CLAWROUTER_CLIENT"] == "custom-host/9.9"


# ---------------------------------------------------------------------------
# Auth-rail guards. Both of these are money bugs when they regress: one spends
# the wallet a customer parked, the other bills the account they logged out of.
# ---------------------------------------------------------------------------

VALID_KEY = "brk_live_" + "a" * 48


def _configure_key(api_key):
    api_key.CORE_API_KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    api_key.CORE_API_KEY_FILE.write_text(VALID_KEY + "\n")


def _install_fake_proxy(supervisor, version: str):
    """Lay down a pre-installed @blockrun/clawrouter of *version*."""
    root = supervisor._npm_root() / "node_modules"
    pkg = root / "@blockrun" / "clawrouter"
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "package.json").write_text(json.dumps({"version": version}))
    binary = root / ".bin" / "clawrouter"
    binary.parent.mkdir(parents=True, exist_ok=True)
    binary.write_text("#!/bin/sh\n")
    binary.chmod(0o755)
    return str(binary)


def test_desired_auth_mode_follows_the_key(isolated_home):
    from clawrouter_hermes import api_key, proxy_supervisor

    assert proxy_supervisor.desired_auth_mode() == "wallet"
    _configure_key(api_key)
    assert proxy_supervisor.desired_auth_mode() == "api-key"


def test_stale_preinstall_is_bypassed_when_a_key_is_configured(isolated_home):
    """<0.12.268 ignores BLOCKRUN_API_KEY and signs x402 from the wallet.

    Launching it with a key configured spends USDC the user believed was
    parked, and says nothing about it — so the fast path has to lose here."""
    from clawrouter_hermes import api_key, proxy_supervisor

    _install_fake_proxy(proxy_supervisor, "0.12.261")
    _configure_key(api_key)

    argv, cwd = proxy_supervisor._spawn_cmd(8402)
    assert argv[0] == "npx"
    assert "@blockrun/clawrouter@latest" in argv
    assert cwd is None


def test_current_preinstall_is_still_the_fast_path(isolated_home):
    from clawrouter_hermes import api_key, proxy_supervisor

    binary = _install_fake_proxy(proxy_supervisor, "0.12.269")
    _configure_key(api_key)

    argv, _ = proxy_supervisor._spawn_cmd(8402)
    assert argv[0] == binary


def test_stale_preinstall_is_fine_for_a_wallet_user(isolated_home):
    """The version floor exists for API-key mode only — a wallet user on an
    old proxy is not being mischarged, just out of date."""
    from clawrouter_hermes import proxy_supervisor

    binary = _install_fake_proxy(proxy_supervisor, "0.12.261")

    argv, _ = proxy_supervisor._spawn_cmd(8402)
    assert argv[0] == binary


def test_local_proxy_version_parses_and_tolerates_junk(isolated_home):
    from clawrouter_hermes import proxy_supervisor

    assert proxy_supervisor.local_proxy_version() is None
    _install_fake_proxy(proxy_supervisor, "0.12.269")
    assert proxy_supervisor.local_proxy_version() == (0, 12, 269)
    _install_fake_proxy(proxy_supervisor, "1.0.0-rc.2")
    assert proxy_supervisor.local_proxy_version() == (1, 0, 0)


def test_claim_port_skips_a_proxy_on_the_other_rail(isolated_home):
    """Reusing a wallet proxy for an API-key user bills the wrong account —
    the same rule the proxy enforces on its own reuse path."""
    from clawrouter_hermes import proxy_supervisor

    # :8402 answers and is a wallet proxy; :8403 is free.
    def fake_probe(base_url, timeout=0.5):
        return "8402" in base_url

    def fake_health(root_url, timeout=0.5):
        return {"status": "ok", "wallet": "0xabc"} if "8402" in root_url else None

    with patch.object(proxy_supervisor, "_probe", fake_probe), \
         patch.object(proxy_supervisor, "_health", fake_health), \
         patch.object(proxy_supervisor, "_port_free", lambda port: port != 8402):
        assert proxy_supervisor._claim_port("wallet") == 8402
        assert proxy_supervisor._claim_port("api-key") == 8403


def test_claim_port_reuses_a_matching_api_key_proxy(isolated_home):
    from clawrouter_hermes import proxy_supervisor

    with patch.object(proxy_supervisor, "_probe", lambda b, timeout=0.5: "8402" in b), \
         patch.object(
             proxy_supervisor, "_health",
             lambda r, timeout=0.5: {"status": "ok", "authMode": "api-key"},
         ):
        assert proxy_supervisor._claim_port("api-key") == 8402


def test_auth_mode_of_treats_a_pre_0_12_268_health_as_wallet(isolated_home):
    """Older proxies report no authMode at all, and the only rail they had was
    the wallet."""
    from clawrouter_hermes import proxy_supervisor

    assert proxy_supervisor._auth_mode_of(None) == "wallet"
    assert proxy_supervisor._auth_mode_of({"status": "ok", "wallet": "0x"}) == "wallet"
    assert proxy_supervisor._auth_mode_of({"authMode": "api-key"}) == "api-key"


def test_stop_kills_the_whole_process_group(isolated_home):
    """``stop`` must reap the proxy npx spawned, not just the npx wrapper.

    The proxy runs as ``npx -y @blockrun/clawrouter``, and npx execs the real
    binary as a child. Terminating only the wrapper left a live proxy holding
    the port — and, on the API-key rail, one that kept billing the account
    after ``logout``. Observed on 2026-09-05: ``stop()`` returned, and
    ``node .../clawrouter --port 8403`` was still serving ``/health`` with
    ``authMode: api-key``.
    """
    import os
    import signal
    import subprocess
    import time

    from clawrouter_hermes import proxy_supervisor

    # A parent that forks a child and waits — the shape npx gives us.
    proc = subprocess.Popen(
        ["sh", "-c", "sleep 30 & echo $! ; wait"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        start_new_session=True,
    )
    child_pid = int(proc.stdout.readline().strip())
    pgid = os.getpgid(proc.pid)
    os.kill(child_pid, 0)  # the grandchild is alive before we stop anything

    proxy_supervisor._process = proc
    try:
        proxy_supervisor.stop()

        deadline = time.time() + 5
        while time.time() < deadline:
            try:
                os.kill(child_pid, 0)
            except ProcessLookupError:
                break
            time.sleep(0.05)
        else:
            raise AssertionError("child survived stop() — only the wrapper was signalled")

        assert proc.poll() is not None, "wrapper still running after stop()"
    finally:
        proxy_supervisor._process = None
        proxy_supervisor._stop_event.clear()
        for pid in (child_pid, proc.pid):
            try:
                os.kill(pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
        try:
            os.killpg(pgid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
