"""Tiny persisted state used to coordinate between the standalone plugin
and the materialized model-provider plugin (port + routing profile)."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

VALID_PROFILES = ("eco", "auto", "premium")


def _state_dir() -> Path:
    return Path.home() / ".openclaw"


def _state_file() -> Path:
    return _state_dir() / "hermes-plugin.json"


# Backward-compat module-level aliases — read-only at the time of access
# (avoid evaluating at import time so tests can monkeypatch HOME).
def __getattr__(name: str):
    if name == "STATE_DIR":
        return _state_dir()
    if name == "STATE_FILE":
        return _state_file()
    raise AttributeError(name)


def _read() -> dict:
    f = _state_file()
    if not f.is_file():
        return {}
    try:
        return json.loads(f.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        logger.debug("state read failed: %s", exc)
        return {}


def _write(data: dict) -> None:
    d = _state_dir()
    d.mkdir(parents=True, exist_ok=True)
    f = _state_file()
    tmp = f.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True))
    os.replace(tmp, f)


def get_port() -> int:
    return int(_read().get("port") or 8402)


def set_port(port: int) -> None:
    data = _read()
    data["port"] = int(port)
    _write(data)


def get_profile() -> str:
    return str(_read().get("profile") or "auto").lower()


def set_profile(profile: str) -> str:
    profile = profile.lower().strip()
    if profile not in VALID_PROFILES:
        raise ValueError(
            f"Invalid routing profile '{profile}'. Choose one of {VALID_PROFILES}."
        )
    data = _read()
    data["profile"] = profile
    _write(data)
    return profile


def proxy_base_url() -> str:
    override = os.environ.get("CLAWROUTER_PROXY_URL", "").strip()
    if override:
        return override.rstrip("/")
    return f"http://127.0.0.1:{get_port()}/v1"


def proxy_root_url() -> str:
    """Same as ``proxy_base_url`` minus the trailing ``/v1``."""
    base = proxy_base_url()
    if base.endswith("/v1"):
        return base[:-3]
    return base


def autospawn_enabled() -> bool:
    raw = os.environ.get("HERMES_CLAWROUTER_AUTOSPAWN", "").strip().lower()
    if raw in {"0", "false", "no", "off"}:
        return False
    return True


def update(updates: dict) -> dict:
    data = _read()
    data.update(updates)
    _write(data)
    return data


def all_state() -> dict:
    return _read()
