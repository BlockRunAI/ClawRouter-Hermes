"""Tool handlers that forward to the local ClawRouter proxy.

All handlers follow the Hermes contract: ``def name(args: dict, **kwargs)
-> str`` returning a JSON-encoded string, never raising. Connection and
payment errors are caught and surfaced as ``{"ok": false, "error": ...,
"hint": ...}``.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

import httpx

from . import proxy_supervisor, state

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT_S = 300.0  # video gen can be slow


def _ok(payload: Any) -> str:
    return json.dumps({"ok": True, "result": payload})


def _err(message: str, *, hint: Optional[str] = None, status: Optional[int] = None) -> str:
    body: dict[str, Any] = {"ok": False, "error": message}
    if hint:
        body["hint"] = hint
    if status is not None:
        body["status"] = status
    return json.dumps(body)


def _post(path: str, body: dict, *, timeout: float = _DEFAULT_TIMEOUT_S) -> str:
    """Shared POST helper. Spawns the proxy if needed and translates errors."""
    status_obj = proxy_supervisor.ensure_running()
    if not status_obj.reachable:
        return _err(
            status_obj.error or "ClawRouter proxy unreachable",
            hint=(
                "Run `hermes clawrouter doctor` to diagnose, or start the "
                "proxy manually: npx @blockrun/clawrouter"
            ),
        )

    url = f"{status_obj.base_url}{path}"
    try:
        resp = httpx.post(
            url,
            json=body,
            timeout=timeout,
            headers={"Authorization": "Bearer hermes-plugin"},
        )
    except httpx.ConnectError as exc:
        return _err(
            f"Cannot reach ClawRouter proxy at {url}: {exc}",
            hint="The proxy may have crashed. Try again or run `hermes clawrouter doctor`.",
        )
    except httpx.HTTPError as exc:
        return _err(f"HTTP error calling {url}: {exc}")

    if resp.status_code == 402:
        return _err(
            "Payment required — ClawRouter wallet may be empty.",
            hint=(
                "Fund USDC on Base or Solana, then retry. "
                "Check balance: `hermes clawrouter wallet`."
            ),
            status=402,
        )
    if not resp.is_success:
        snippet = (resp.text or "")[:500]
        return _err(
            f"ClawRouter returned HTTP {resp.status_code}: {snippet}",
            status=resp.status_code,
        )

    try:
        data = resp.json()
    except ValueError:
        return _ok({"raw": resp.text})
    return _ok(data)


def image_generate(args: dict, **_: Any) -> str:
    prompt = (args or {}).get("prompt", "").strip()
    if not prompt:
        return _err("Missing required argument: prompt")

    body: dict[str, Any] = {"prompt": prompt}
    for field in ("model", "size", "n"):
        if args.get(field) is not None:
            body[field] = args[field]
    return _post("/images/generations", body)


def video_generate(args: dict, **_: Any) -> str:
    prompt = (args or {}).get("prompt", "").strip()
    if not prompt:
        return _err("Missing required argument: prompt")

    body: dict[str, Any] = {"prompt": prompt}
    for field in ("model", "duration", "resolution"):
        if args.get(field) is not None:
            body[field] = args[field]
    return _post("/videos/generations", body)


def web_search(args: dict, **_: Any) -> str:
    query = (args or {}).get("query", "").strip()
    if not query:
        return _err("Missing required argument: query")

    body: dict[str, Any] = {"query": query}
    if args.get("num_results") is not None:
        body["num_results"] = args["num_results"]
    if args.get("include_domains"):
        body["include_domains"] = args["include_domains"]
    if args.get("exclude_domains"):
        body["exclude_domains"] = args["exclude_domains"]
    if args.get("include_text") is not None:
        body["include_text"] = bool(args["include_text"])
    return _post("/exa/search", body)


def proxy_stats(**_: Any) -> dict:
    """Helper used by the slash command — pure JSON dict (not stringified)."""
    status_obj = proxy_supervisor.ensure_running(autospawn=False)
    if not status_obj.reachable:
        return {
            "ok": False,
            "error": status_obj.error or "proxy not running",
            "base_url": status_obj.base_url,
            "port": state.get_port(),
        }
    try:
        resp = httpx.get(f"{status_obj.base_url}/stats", timeout=5.0)
        if resp.is_success:
            return {"ok": True, "stats": resp.json()}
        return {"ok": False, "error": f"HTTP {resp.status_code}", "status": resp.status_code}
    except httpx.HTTPError as exc:
        return {"ok": False, "error": str(exc)}
