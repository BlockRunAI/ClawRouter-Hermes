"""proxy_supervisor.py — probing, port claiming, env overrides.

We don't actually spawn ``npx`` in tests (no Node guarantee in CI). Instead
we monkeypatch :func:`_node_available` and :func:`_spawn` to drive the
supervisor through its branches.
"""

from __future__ import annotations

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
