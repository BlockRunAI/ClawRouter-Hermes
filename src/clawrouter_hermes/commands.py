"""Slash command handlers: ``/clawrouter wallet|stats|route|status|help``.

Each handler receives the raw argument string (everything after the
command word) and returns a string to display in the chat session.
"""

from __future__ import annotations

import json
from typing import Callable, Dict

from . import proxy_supervisor, state, tools, wallet


HELP_TEXT = (
    "ClawRouter commands:\n"
    "  /clawrouter wallet            Show address + USDC balance\n"
    "  /clawrouter wallet base       Switch payment chain to Base\n"
    "  /clawrouter wallet solana     Switch payment chain to Solana\n"
    "  /clawrouter stats             Show proxy usage stats\n"
    "  /clawrouter status            Show proxy health\n"
    "  /clawrouter route <eco|auto|premium>   Set routing profile\n"
    "  /clawrouter help              This message"
)


def _handle_wallet(raw_args: str) -> str:
    args = (raw_args or "").strip().lower()

    if args in {"base", "solana"}:
        try:
            chain = wallet.set_payment_chain(args)
        except ValueError as exc:
            return f"❌ {exc}"

        proxy_supervisor.stop()
        status = proxy_supervisor.ensure_running()
        if status.reachable:
            addrs = wallet.load_addresses()
            addr = addrs.evm if args == "base" else addrs.solana
            return (
                f"✅ Payment chain switched to *{chain.capitalize()}*.\n"
                f"Proxy restarted.\n\n"
                f"*{chain.capitalize()} Address:* `{addr}`"
            )
        return f"⚠️ Chain set to *{chain.capitalize()}* but proxy failed to restart. Run `/clawrouter status`."

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
        f"  Error:           {s.error or '—'}"
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


_SUB_HANDLERS: Dict[str, Callable[[str], str]] = {
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
