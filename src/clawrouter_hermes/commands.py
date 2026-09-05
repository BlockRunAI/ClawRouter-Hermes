"""Slash command handlers: ``/clawrouter wallet|stats|route|status|help``.

Each handler receives the raw argument string (everything after the
command word) and returns a string to display in the chat session.
"""

from __future__ import annotations

import json
from typing import Callable, Dict

from . import api_key, proxy_supervisor, state, tools, wallet


HELP_TEXT = (
    "ClawRouter commands:\n"
    "  /clawrouter account           Show which rail you're paying on\n"
    "  /clawrouter wallet            Show address + USDC balance\n"
    "  /clawrouter wallet solana     Switch payment chain to Solana\n"
    "  /clawrouter wallet base       Switch payment chain to Base\n"
    "  /clawrouter stats             Show proxy usage stats\n"
    "  /clawrouter status            Show proxy health\n"
    "  /clawrouter route <eco|auto|premium>   Set routing profile\n"
    "  /clawrouter logout            Drop the API key, go back to the wallet\n"
    "  /clawrouter help              This message\n"
    "\n"
    "Paying by card instead of USDC? Mint a key at\n"
    f"{api_key.PORTAL_KEYS_URL}, then run `hermes-clawrouter login <key>`\n"
    "in a terminal — never paste a key into a chat."
)


def _handle_account(_: str) -> str:
    """Which rail is this machine on, and where to change it."""
    status = proxy_supervisor.status()
    mode = status.auth_mode
    if mode == "api-key":
        body = api_key.format_summary(api_key.summary())
        if status.reachable and status.gateway:
            body += f"\n\n  Live proxy: {status.base_url} → {status.gateway}"
        return body
    return (
        "👛 *Paying with the x402 wallet*\n\n"
        "  USDC is signed per request from the local wallet — no account "
        "anywhere.\n"
        "  See it with `/clawrouter wallet`.\n\n"
        f"  Prefer a card? Sign in at {api_key.PORTAL_URL}, mint a key at\n"
        f"  {api_key.PORTAL_KEYS_URL}, then run "
        "`hermes-clawrouter login <key>`.\n"
        "  Nothing is deleted — `logout` puts you back here."
    )


def _handle_wallet(raw_args: str) -> str:
    args = (raw_args or "").strip().lower()

    if not args and proxy_supervisor.status().auth_mode == "api-key":
        # A wallet balance is not what "how am I paying" means here, and a
        # $0.00 wallet reads as a broken setup when the account is what pays.
        return (
            api_key.format_summary(api_key.summary())
            + "\n\n  The x402 wallet is idle while a key is configured. "
            "`/clawrouter wallet solana`\n  or `base` still switches the chain "
            "it would use after `hermes-clawrouter logout`."
        )

    if args in wallet.VALID_CHAINS:
        try:
            chain = wallet.set_payment_chain(args)
        except ValueError as exc:
            return f"❌ {exc}"

        proxy_supervisor.stop()
        import time
        time.sleep(2)
        status = proxy_supervisor.ensure_running()
        if status.reachable:
            addrs = wallet.load_addresses()
            addr = addrs.evm if args == "base" else addrs.solana
            return (
                f"✅ Payment chain switched to *{chain.capitalize()}* for all "
                f"ClawRouter clients on this machine (shared wallet).\n"
                f"Proxy restarted.\n\n"
                f"*{chain.capitalize()} Address:* `{addr}`"
            )
        return (
            f"⚠️ Chain set to *{chain.capitalize()}* (machine-wide) but the proxy "
            f"failed to restart. Run `/clawrouter status`."
        )

    return wallet.format_summary(wallet.wallet_summary())


def _handle_stats(_: str) -> str:
    return json.dumps(tools.proxy_stats(), indent=2)


def _handle_status(_: str) -> str:
    s = proxy_supervisor.status()
    profile = state.get_profile()
    flag = "✓" if s.reachable else "✗"
    return (
        f"{flag} ClawRouter proxy\n"
        f"  Base URL:        {s.base_url}\n"
        f"  Port:            {s.port}\n"
        f"  Reachable:       {s.reachable}\n"
        f"  Managed by us:   {s.managed}  (pid={s.pid})\n"
        f"  Routing profile: {profile}\n"
        f"  Auth mode:       {s.auth_mode}"
        + (f" ({s.api_key_label} → {s.gateway})" if s.auth_mode == "api-key" and s.gateway else "")
        + f"\n  Error:           {s.error or '—'}"
    )


def _handle_route(raw_args: str) -> str:
    arg = (raw_args or "").strip().lower()
    if not arg or arg in {"help", "?"}:
        return (
            "Usage: /clawrouter route <eco|auto|premium>\n"
            f"Current profile: {state.get_profile()}"
        )
    try:
        new_profile = state.set_profile(arg)
    except ValueError as exc:
        return f"❌ {exc}"
    return (
        f"✓ Routing profile set to '{new_profile}'.\n"
        "Takes effect on next proxy spawn — run "
        "`/clawrouter status` then restart the proxy if you want it immediately."
    )


def _handle_login(_: str) -> str:
    """Deliberately refuses. A slash command's arguments live in the chat
    transcript — on Telegram that is a server-side message history the user
    cannot fully delete, and an API key there is a bearer credential for their
    money. The terminal is the only place this should be typed.
    """
    return (
        "🔒 Not here — a key pasted into a chat stays in the transcript.\n\n"
        "Run this in a terminal instead:\n"
        "  `hermes-clawrouter login brk_live_…`\n\n"
        f"Mint one at {api_key.PORTAL_KEYS_URL}. "
        "If you already pasted a key\nin chat, revoke it there and mint a new one."
    )


def _handle_logout(_: str) -> str:
    result = api_key.clear()
    if not result["removed"] and not result["env_still_set"]:
        return "No BlockRun API key was configured — already on the x402 wallet."
    lines = ["✅ Back on the x402 wallet."]
    for path in result["removed"]:
        lines.append(f"  Removed {path}")
    if result["env_still_set"]:
        lines.append(
            f"  ⚠ {api_key.ENV_API_KEY} is still set in the environment — only "
            "your shell can unset that one."
        )
    lines.append("  Restart the proxy to take effect: `/clawrouter status`.")
    return "\n".join(lines)


_SUB_HANDLERS: Dict[str, Callable[[str], str]] = {
    "account": _handle_account,
    "login": _handle_login,
    "logout": _handle_logout,
    "wallet": _handle_wallet,
    "stats": _handle_stats,
    "status": _handle_status,
    "route": _handle_route,
    "help": lambda _: HELP_TEXT,
    "?": lambda _: HELP_TEXT,
    "": lambda _: HELP_TEXT,
}


def clawrouter_dispatch(raw_args: str) -> str:
    """Single registered slash command: ``/clawrouter <sub> [args...]``."""
    parts = (raw_args or "").strip().split(maxsplit=1)
    sub = parts[0].lower() if parts else ""
    rest = parts[1] if len(parts) > 1 else ""
    handler = _SUB_HANDLERS.get(sub)
    if handler is None:
        return f"Unknown subcommand: {sub!r}\n{HELP_TEXT}"
    return handler(rest)
