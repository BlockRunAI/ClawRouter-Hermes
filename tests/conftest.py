"""Pytest fixtures — isolate the plugin from the user's real ~/.openclaw."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture
def isolated_home(tmp_path, monkeypatch):
    """Redirect HOME to a clean tmp dir for the duration of a test."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("BLOCKRUN_WALLET_KEY", raising=False)
    monkeypatch.delenv("CLAWROUTER_PROXY_URL", raising=False)
    monkeypatch.delenv("HERMES_CLAWROUTER_AUTOSPAWN", raising=False)

    # Path.home() resolves $HOME, but some modules cache the value at import
    # time. Reload state/wallet so the new HOME wins.
    for mod_name in [
        "clawrouter_hermes.state",
        "clawrouter_hermes.wallet",
        "clawrouter_hermes.proxy_supervisor",
        "clawrouter_hermes.cli",
    ]:
        if mod_name in sys.modules:
            del sys.modules[mod_name]
    yield tmp_path
