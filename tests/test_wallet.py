"""wallet.py — mnemonic read + BIP-44 derivation.

The expected addresses below are cross-verified against ClawRouter's TS
implementation (``ClawRouter/src/wallet.ts``) by ``scripts/verify_derivation.mjs``.
Both languages produce identical bytes for the same BIP-39 mnemonic.
"""

from __future__ import annotations

import os

import pytest

# Canonical BIP-39 test vector (Trezor "abandon" mnemonic) — public, no funds.
TEST_MNEMONIC = (
    "abandon abandon abandon abandon abandon abandon abandon abandon "
    "abandon abandon abandon about"
)
# These exact strings are emitted by scripts/verify_derivation.mjs running
# against ClawRouter/src/wallet.ts. Do not soften — byte parity is the contract.
EXPECTED_EVM_ADDR = "0x9858EfFD232B4033E47d90003D41EC34EcaEda94"
EXPECTED_SOLANA_ADDR = "HAgk14JpMQLgt6rVgv7cBQFJWFto5Dqxi472uT3DKpqk"


def test_no_wallet_raises(isolated_home):
    from clawrouter_hermes import wallet

    with pytest.raises(FileNotFoundError):
        wallet.load_addresses()


def test_mnemonic_derivation_matches_ts(isolated_home):
    """Python derivation must produce the exact addresses TS produces."""
    from clawrouter_hermes import wallet

    wallet.WALLET_DIR.mkdir(parents=True, exist_ok=True)
    wallet.MNEMONIC_FILE.write_text(TEST_MNEMONIC + "\n")

    addrs = wallet.load_addresses()
    assert addrs.source == "file"
    assert addrs.evm == EXPECTED_EVM_ADDR, (
        "EVM derivation diverged from ClawRouter TS — "
        "run scripts/verify_derivation.mjs to compare"
    )
    assert addrs.solana == EXPECTED_SOLANA_ADDR, (
        "Solana derivation diverged from ClawRouter TS — "
        "run scripts/verify_derivation.mjs to compare"
    )


def test_env_override_evm_only(isolated_home, monkeypatch):
    from clawrouter_hermes import wallet

    # Random known private key — has no funds.
    monkeypatch.setenv(
        "BLOCKRUN_WALLET_KEY",
        "0x0000000000000000000000000000000000000000000000000000000000000001",
    )
    addrs = wallet.load_addresses()
    assert addrs.source == "env"
    assert addrs.evm.startswith("0x")
    assert "unavailable" in addrs.solana.lower()


def test_invalid_mnemonic_raises(isolated_home):
    from clawrouter_hermes import wallet

    wallet.WALLET_DIR.mkdir(parents=True, exist_ok=True)
    wallet.MNEMONIC_FILE.write_text("not actually a valid mnemonic\n")

    with pytest.raises(ValueError, match="Invalid BIP-39"):
        wallet.load_addresses()


def test_format_summary_error_path(isolated_home):
    from clawrouter_hermes import wallet

    out = wallet.format_summary({"ok": False, "error": "boom"})
    assert "❌" in out
    assert "boom" in out


def test_format_summary_surfaces_shared_wallet_and_backup(isolated_home):
    from clawrouter_hermes import wallet

    summary = {
        "ok": True,
        "source": "file",
        "evm": {"address": "0xabc", "usdc_balance": 1.0, "chain": "base"},
        "solana": {"address": "SoLabc", "usdc_balance": None, "chain": "solana"},
        "mnemonic_path": "/home/u/.openclaw/blockrun/mnemonic",
    }
    out = wallet.format_summary(summary)
    # Transparency: shared with OpenClaw, where the keys live, and backup nudge.
    assert "OpenClaw" in out
    assert "Back up your mnemonic" in out
    assert summary["mnemonic_path"] in out
    # Active payment chain + that switching is machine-wide.
    assert "Paying on" in out
    assert "all ClawRouter clients" in out


def test_payment_chain_defaults_to_base(isolated_home):
    from clawrouter_hermes import wallet

    # No file written yet → proxy's loadPaymentChain() also defaults to "base".
    assert wallet.current_payment_chain() == "base"


def test_payment_chain_round_trip(isolated_home):
    from clawrouter_hermes import wallet

    # Mixed case / surrounding space must normalize to the bare lowercase token
    # the proxy's loadPaymentChain() compares against (content.trim() == "solana").
    assert wallet.set_payment_chain("  Solana ") == "solana"
    assert wallet.CHAIN_FILE.read_text(encoding="utf-8") == "solana"
    assert wallet.current_payment_chain() == "solana"

    assert wallet.set_payment_chain("base") == "base"
    assert wallet.current_payment_chain() == "base"


def test_set_payment_chain_rejects_unknown(isolated_home):
    from clawrouter_hermes import wallet

    with pytest.raises(ValueError, match="Unknown chain"):
        wallet.set_payment_chain("ethereum")
