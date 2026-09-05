"""BlockRun API-key auth — the second way to pay, alongside the x402 wallet.

A wallet signs a USDC micropayment per call; an API key draws on account
credit the user topped up with a card at https://user.blockrun.ai. Same
catalog, same model ids, same OpenAI-compatible shape — a different host and
a different auth header:

    wallet   → https://sol.blockrun.ai/api  |  https://blockrun.ai/api   (x402)
    API key  → https://api.blockrun.ai                                  (Bearer brk_…)

This module is a faithful Python mirror of ``ClawRouter/src/api-key.ts``: the
same resolution order, the same validity rule, the same mask. It has to be —
the proxy this plugin spawns resolves the key with that TS code, so a Python
answer that disagreed would make the plugin describe an auth mode the proxy
is not actually running in.

Resolution order, highest first:
  1. ``BLOCKRUN_API_KEY`` environment variable
  2. BlockRun Core — ``~/.blockrun/.api-key``, shared with other BlockRun products
  3. Legacy ClawRouter location — ``~/.openclaw/blockrun/api-key``

The plugin never sends the key anywhere itself except ``api.blockrun.ai``
during ``login``/``doctor`` verification: normal traffic goes to the local
proxy, which attaches the bearer token upstream.

@see https://user.blockrun.ai/dashboard/keys — where a user mints one
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

ENV_API_KEY = "BLOCKRUN_API_KEY"

#: Where a user signs up, tops up with a card, and mints keys.
PORTAL_URL = "https://user.blockrun.ai"
PORTAL_KEYS_URL = f"{PORTAL_URL}/dashboard/keys"
PORTAL_CREDITS_URL = f"{PORTAL_URL}/dashboard/credits"
PORTAL_ACTIVITY_URL = f"{PORTAL_URL}/dashboard/activity"

#: Deliberately loose on the body, strict on the prefix — same rule as the TS
#: side. The server accepts anything starting with ``brk_`` and today mints
#: ``brk_live_<base62>``; pinning an exact length here would reject a future
#: ``brk_test_`` and lock users out over a format change that is not ours to
#: make. The prefix is what stops a wallet key, an OpenAI key or a pasted
#: password from being stored as a BlockRun credential and then failing as an
#: opaque 401.
_KEY_RE = re.compile(r"^brk_[A-Za-z0-9_-]{8,}$")


def default_gateway() -> str:
    """The API-key gateway.

    Note there is no ``/api`` path segment: api.blockrun.ai serves ``/v1/*``
    at its root, unlike blockrun.ai which serves it under ``/api``.
    Overridable for staging deploys, same as the wallet gateways.
    """
    override = os.environ.get("BLOCKRUN_API_BASE_URL", "").strip()
    return override.rstrip("/") if override else "https://api.blockrun.ai"


def _core_key_file() -> Path:
    """Canonical cross-product key file, alongside the Core wallet material."""
    return Path.home() / ".blockrun" / ".api-key"


def _legacy_key_file() -> Path:
    """Legacy ClawRouter-local key file."""
    return Path.home() / ".openclaw" / "blockrun" / "api-key"


def __getattr__(name: str):
    # Lazy so tests can monkeypatch HOME after import.
    if name == "CORE_API_KEY_FILE":
        return _core_key_file()
    if name == "LEGACY_API_KEY_FILE":
        return _legacy_key_file()
    raise AttributeError(name)


@dataclass(frozen=True)
class ApiKeyResolution:
    key: str
    source: str  # "env" | "core" | "legacy"

    @property
    def masked(self) -> str:
        return mask(self.key)


def is_valid(value: Optional[str]) -> bool:
    """Is this a well-formed BlockRun key?"""
    if not isinstance(value, str):
        return False
    return bool(_KEY_RE.match(value.strip()))


def mask(key: str) -> str:
    """Render a key for a status table: enough to tell two keys apart, never
    enough to use. The portal labels keys by their first 14 characters, so the
    head matches what the user sees on the dashboard.
    """
    trimmed = key.strip()
    if len(trimmed) <= 18:
        return f"{trimmed[:8]}…"
    return f"{trimmed[:14]}…{trimmed[-4:]}"


def _read_optional(path: Path) -> Optional[str]:
    try:
        text = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return text or None


def resolve() -> Optional[ApiKeyResolution]:
    """Resolve the configured API key without creating anything.

    Returns ``None`` when no key is configured — the normal state for a wallet
    user, not an error. A file that exists but holds something that is not a
    key is logged and skipped rather than used: a malformed credential is a
    401 per request, and an unexplained 401 is the hardest failure mode there
    is to diagnose.
    """
    env_key = os.environ.get(ENV_API_KEY, "").strip()
    if env_key:
        if is_valid(env_key):
            return ApiKeyResolution(key=env_key, source="env")
        logger.warning(
            "%s is set but does not look like a BlockRun key (expected brk_…) — ignoring.",
            ENV_API_KEY,
        )

    for path, source in ((_core_key_file(), "core"), (_legacy_key_file(), "legacy")):
        stored = _read_optional(path)
        if stored is None:
            continue
        if is_valid(stored):
            return ApiKeyResolution(key=stored, source=source)
        logger.warning(
            "%s does not contain a BlockRun key (expected brk_…) — ignoring.", path
        )

    return None


def save(key: str) -> Path:
    """Persist a key to BlockRun Core so every BlockRun product on this machine
    picks it up. Written 0600 — it is a bearer credential for the user's money.
    """
    trimmed = key.strip()
    if not is_valid(trimmed):
        raise ValueError(
            'Not a BlockRun API key: expected it to start with "brk_". '
            f"Mint one at {PORTAL_KEYS_URL}"
        )
    path = _core_key_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(trimmed + "\n", encoding="utf-8")
    path.chmod(0o600)
    return path


def clear() -> dict:
    """Remove every stored key.

    Returns the files actually deleted so the caller can say what changed; an
    env-var key is reported separately because only the user's shell can unset
    that one.
    """
    removed: list[str] = []
    for path in (_core_key_file(), _legacy_key_file()):
        if _read_optional(path) is None and not path.is_file():
            continue
        try:
            path.unlink()
        except OSError as exc:
            logger.debug("could not remove %s: %s", path, exc)
            continue
        removed.append(str(path))
    return {
        "removed": removed,
        "env_still_set": bool(os.environ.get(ENV_API_KEY, "").strip()),
    }


def verify(key: str, *, timeout: float = 10.0) -> tuple[Optional[bool], str]:
    """Prove the key actually works, by listing models as its bearer.

    Returns ``(accepted, detail)``. ``accepted`` is ``None`` when the gateway
    could not be reached at all — an unreachable gateway is not a rejected
    key, and reporting it as one would send a user to mint a replacement for a
    credential that is fine.
    """
    url = f"{default_gateway()}/v1/models"
    try:
        resp = httpx.get(url, headers={"Authorization": f"Bearer {key}"}, timeout=timeout)
    except httpx.HTTPError as exc:
        return None, f"{default_gateway()} unreachable: {exc}"
    if resp.status_code == 200:
        try:
            count = len(resp.json().get("data") or [])
        except ValueError:
            count = 0
        return True, f"{default_gateway()} accepted the key ({count} models)"
    if resp.status_code in (401, 403):
        return False, (
            f"{default_gateway()} rejected the key (HTTP {resp.status_code}) — "
            f"it may be revoked or mistyped. Mint a new one at {PORTAL_KEYS_URL}"
        )
    return None, f"{default_gateway()} returned HTTP {resp.status_code}"


def summary() -> dict:
    """JSON-serializable API-key state, for slash commands and ``doctor``."""
    resolved = resolve()
    if resolved is None:
        return {
            "configured": False,
            "gateway": default_gateway(),
            "portal": PORTAL_URL,
            "keys_url": PORTAL_KEYS_URL,
            "credits_url": PORTAL_CREDITS_URL,
        }
    return {
        "configured": True,
        "masked": resolved.masked,
        "source": resolved.source,
        "gateway": default_gateway(),
        "portal": PORTAL_URL,
        "keys_url": PORTAL_KEYS_URL,
        "credits_url": PORTAL_CREDITS_URL,
        "activity_url": PORTAL_ACTIVITY_URL,
    }


def format_summary(data: dict) -> str:
    """Pretty-print :func:`summary` output for terminals and chat."""
    if not data.get("configured"):
        return (
            "🔑 *BlockRun API key*\n\n"
            "  Not configured — this machine pays with the x402 wallet.\n\n"
            f"  Want to pay by card instead? Sign in at {PORTAL_URL}, "
            f"mint a key at {PORTAL_KEYS_URL},\n"
            "  then run `hermes-clawrouter login brk_live_…`."
        )
    source_label = {
        "env": f"{ENV_API_KEY} env var",
        "core": str(_core_key_file()),
        "legacy": str(_legacy_key_file()),
    }.get(str(data.get("source")), str(data.get("source")))
    return (
        "🔑 *BlockRun API key*\n\n"
        f"  Key:      `{data.get('masked')}`\n"
        f"  From:     {source_label}\n"
        f"  Gateway:  {data.get('gateway')}\n"
        f"  Billing:  account credit — top up at {data.get('credits_url')}\n"
        f"  Activity: {data.get('activity_url')}\n\n"
        "  A key wins over a wallet whenever both are present. Nothing is "
        "deleted —\n  `hermes-clawrouter logout` puts you back on the wallet."
    )
