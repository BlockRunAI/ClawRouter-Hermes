"""state.py — persistence + env-var-driven helpers."""

from __future__ import annotations

import json

import pytest


def test_defaults(isolated_home):
    from clawrouter_hermes import state

    assert state.get_port() == 8402
    assert state.get_profile() == "auto"
    assert state.proxy_base_url() == "http://127.0.0.1:8402/v1"
    assert state.autospawn_enabled() is True


def test_set_port_persists(isolated_home):
    from clawrouter_hermes import state

    state.set_port(8407)
    assert state.get_port() == 8407
    on_disk = json.loads((isolated_home / ".openclaw" / "hermes-plugin.json").read_text())
    assert on_disk["port"] == 8407


def test_set_profile_validates(isolated_home):
    from clawrouter_hermes import state

    assert state.set_profile("eco") == "eco"
    assert state.get_profile() == "eco"
    with pytest.raises(ValueError):
        state.set_profile("nope")


def test_proxy_url_env_override(isolated_home, monkeypatch):
    from clawrouter_hermes import state

    monkeypatch.setenv("CLAWROUTER_PROXY_URL", "https://blockrun.ai/v1/")
    assert state.proxy_base_url() == "https://blockrun.ai/v1"


def test_autospawn_disable(isolated_home, monkeypatch):
    from clawrouter_hermes import state

    monkeypatch.setenv("HERMES_CLAWROUTER_AUTOSPAWN", "0")
    assert state.autospawn_enabled() is False
