"""Live RPC integration tests — skipped by default.

Run with ``CLAWROUTER_LIVE_RPC=1 pytest tests/test_live_rpc.py -v`` to hit
Base and Solana mainnet RPCs and confirm USDC balance fetching works
end-to-end.

These tests use the Trezor "abandon" wallet (publicly known, no funds) so
they assert the RPC call shape — returning ``0.0`` proves the JSON-RPC
request succeeded and we parsed the response; ``None`` would mean the call
itself failed.
"""

from __future__ import annotations

import os

import pytest

LIVE = os.environ.get("CLAWROUTER_LIVE_RPC", "").strip().lower() in {"1", "true", "yes"}

EVM_ADDR = "0x9858EfFD232B4033E47d90003D41EC34EcaEda94"
SOLANA_ADDR = "HAgk14JpMQLgt6rVgv7cBQFJWFto5Dqxi472uT3DKpqk"


pytestmark = pytest.mark.skipif(
    not LIVE,
    reason="Set CLAWROUTER_LIVE_RPC=1 to run live RPC tests",
)


def test_base_usdc_rpc_reachable():
    from clawrouter_hermes import wallet

    balance = wallet.fetch_usdc_base(EVM_ADDR)
    assert balance is not None, "Base mainnet RPC unreachable or response unparseable"
    assert isinstance(balance, float)
    assert balance >= 0.0


def test_solana_usdc_rpc_reachable():
    from clawrouter_hermes import wallet

    balance = wallet.fetch_usdc_solana(SOLANA_ADDR)
    assert balance is not None, "Solana mainnet RPC unreachable or response unparseable"
    assert isinstance(balance, float)
    assert balance >= 0.0


def test_full_summary_live():
    """End-to-end: load_addresses + both RPCs + format."""
    import tempfile
    from pathlib import Path
    from clawrouter_hermes import wallet

    # Use a fresh HOME so we don't read the user's real mnemonic.
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["HOME"] = tmp
        wallet_dir = Path(tmp) / ".openclaw" / "blockrun"
        wallet_dir.mkdir(parents=True)
        (wallet_dir / "mnemonic").write_text(
            "abandon abandon abandon abandon abandon abandon abandon abandon "
            "abandon abandon abandon about\n"
        )
        # Force fresh path resolution.
        import importlib
        importlib.reload(wallet)

        summary = wallet.wallet_summary()
        assert summary["ok"] is True
        assert summary["evm"]["address"] == EVM_ADDR
        assert summary["solana"]["address"] == SOLANA_ADDR
        # Both balance fetches must have succeeded (returned 0.0 for an unfunded
        # known address — not None).
        assert summary["evm"]["usdc_balance"] is not None
        assert summary["solana"]["usdc_balance"] is not None
