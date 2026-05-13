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
