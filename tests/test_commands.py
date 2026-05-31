"""commands.py — slash command dispatch."""

from __future__ import annotations

from unittest.mock import patch


def test_help_default(isolated_home):
    from clawrouter_hermes import commands

    out = commands.clawrouter_dispatch("")
    assert "wallet" in out
    assert "stats" in out
    assert "route" in out


def test_unknown_subcommand(isolated_home):
    from clawrouter_hermes import commands

    out = commands.clawrouter_dispatch("zappa")
    assert "Unknown" in out


def test_route_round_trip(isolated_home):
    from clawrouter_hermes import commands, state

    out = commands.clawrouter_dispatch("route eco")
    assert "eco" in out
    assert state.get_profile() == "eco"


def test_route_invalid(isolated_home):
    from clawrouter_hermes import commands

    out = commands.clawrouter_dispatch("route nope")
    assert out.startswith("❌")


def test_status_runs_without_proxy(isolated_home):
    from clawrouter_hermes import commands, proxy_supervisor

    with patch.object(proxy_supervisor, "_probe", return_value=False):
        out = commands.clawrouter_dispatch("status")
        assert "ClawRouter proxy" in out
        assert "Reachable:" in out


def _fake_status(reachable, **kw):
    from clawrouter_hermes.proxy_supervisor import ProxyStatus

    return ProxyStatus(
        reachable=reachable,
        base_url="http://127.0.0.1:8402/v1",
        port=8402,
        pid=123 if reachable else None,
        managed=reachable,
        error=None if reachable else "boom",
    )


def test_wallet_switch_chain_restarts_and_persists(isolated_home, monkeypatch):
    from clawrouter_hermes import commands

    # Patch through ``commands.*`` — ``_handle_wallet`` calls these via the
    # module-level imports that ``commands`` bound at its own import time.
    monkeypatch.setattr("time.sleep", lambda *_a, **_k: None)
    monkeypatch.setattr(commands.proxy_supervisor, "stop", lambda: None)
    monkeypatch.setattr(
        commands.proxy_supervisor, "ensure_running", lambda *a, **k: _fake_status(True)
    )

    class _Addrs:
        evm = "0xEVMADDR"
        solana = "SOLADDR"

    monkeypatch.setattr(commands.wallet, "load_addresses", lambda: _Addrs())

    out = commands.clawrouter_dispatch("wallet solana")
    assert "Solana" in out
    assert "SOLADDR" in out
    # Switch is machine-wide (shared wallet), not Hermes-local — say so.
    assert "all ClawRouter clients" in out
    # The file the proxy reads on restart must reflect the new chain.
    assert commands.wallet.current_payment_chain() == "solana"


def test_wallet_switch_chain_proxy_restart_fails(isolated_home, monkeypatch):
    from clawrouter_hermes import commands

    monkeypatch.setattr("time.sleep", lambda *_a, **_k: None)
    monkeypatch.setattr(commands.proxy_supervisor, "stop", lambda: None)
    monkeypatch.setattr(
        commands.proxy_supervisor, "ensure_running", lambda *a, **k: _fake_status(False)
    )

    out = commands.clawrouter_dispatch("wallet base")
    assert "⚠️" in out
    assert "machine-wide" in out
    # Chain is still persisted even when the restart fails.
    assert commands.wallet.current_payment_chain() == "base"


def test_wallet_unknown_arg_falls_through_to_summary(isolated_home):
    from clawrouter_hermes import commands

    # An arg that is neither "base" nor "solana" must not switch chains or
    # crash — it shows the normal wallet summary (here: no wallet → ❌).
    out = commands.clawrouter_dispatch("wallet garbage")
    assert "❌" in out
