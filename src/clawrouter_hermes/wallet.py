"""Read-only wallet accessor.

Mirrors the TS implementation at ClawRouter/src/wallet.ts:
- EVM derivation: BIP-44 ``m/44'/60'/0'/0/0`` (secp256k1)
- Solana derivation: SLIP-10 ``m/44'/501'/0'/0'`` (ed25519, Phantom-compatible)

The plugin never writes — wallet creation stays in the canonical TS CLI
(``npx @blockrun/clawrouter setup``). USDC balances are fetched from
public RPCs.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

ENV_WALLET_KEY = "BLOCKRUN_WALLET_KEY"


def _wallet_dir() -> Path:
    return Path.home() / ".openclaw" / "blockrun"


def _mnemonic_file() -> Path:
    return _wallet_dir() / "mnemonic"


def _wallet_key_file() -> Path:
    return _wallet_dir() / "wallet.key"


def __getattr__(name: str):
    if name == "WALLET_DIR":
        return _wallet_dir()
    if name == "MNEMONIC_FILE":
        return _mnemonic_file()
    if name == "WALLET_KEY_FILE":
        return _wallet_key_file()
    raise AttributeError(name)

USDC_BASE_CONTRACT = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
USDC_BASE_DECIMALS = 6
USDC_SOLANA_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
USDC_SOLANA_DECIMALS = 6

BASE_RPC = "https://mainnet.base.org"
SOLANA_RPC = "https://api.mainnet-beta.solana.com"


@dataclass(frozen=True)
class WalletAddresses:
    evm: str
    solana: str
    source: str  # "file" | "env"


def _read_mnemonic_file() -> Optional[str]:
    path = _mnemonic_file()
    if not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        logger.warning("Cannot read mnemonic at %s: %s", path, exc)
        return None
    return text or None


def _evm_from_priv_hex(priv_hex: str) -> str:
    """Address derivation for the env-var path (BLOCKRUN_WALLET_KEY)."""
    from bip_utils import EthAddr
    from bip_utils.ecc import Secp256k1PrivateKey

    raw = bytes.fromhex(priv_hex.removeprefix("0x"))
    if len(raw) != 32:
        raise ValueError("EVM private key must be 32 bytes")
    sk = Secp256k1PrivateKey.FromBytes(raw)
    return EthAddr.EncodeKey(sk.PublicKey())


def _derive_from_mnemonic(mnemonic: str) -> WalletAddresses:
    from bip_utils import (
        Bip39MnemonicValidator,
        Bip39SeedGenerator,
        Bip44,
        Bip44Changes,
        Bip44Coins,
        EthAddr,
        SolAddr,
        Bip32Slip10Ed25519,
    )

    if not Bip39MnemonicValidator().IsValid(mnemonic):
        raise ValueError("Invalid BIP-39 mnemonic (failed checksum)")

    seed = Bip39SeedGenerator(mnemonic).Generate()

    eth_wallet = (
        Bip44.FromSeed(seed, Bip44Coins.ETHEREUM)
        .Purpose()
        .Coin()
        .Account(0)
        .Change(Bip44Changes.CHAIN_EXT)
        .AddressIndex(0)
    )
    evm_addr = EthAddr.EncodeKey(eth_wallet.PublicKey().RawCompressed().ToBytes())

    sol_ctx = (
        Bip32Slip10Ed25519.FromSeed(seed)
        .DerivePath("m/44'/501'/0'/0'")
    )
    sol_addr = SolAddr.EncodeKey(sol_ctx.PublicKey().RawCompressed().ToBytes()[1:])

    return WalletAddresses(evm=evm_addr, solana=sol_addr, source="file")


def load_addresses() -> WalletAddresses:
    """Return EVM + Solana addresses derived from the canonical wallet.

    Resolution order:
      1. ``BLOCKRUN_WALLET_KEY`` env var (raw EVM hex; Solana address unavailable)
      2. ``~/.openclaw/blockrun/mnemonic`` (BIP-39 24-word phrase)

    Raises ``FileNotFoundError`` when neither source is present so callers
    can surface an actionable "run setup" message.
    """
    env_key = os.environ.get(ENV_WALLET_KEY, "").strip()
    if env_key:
        return WalletAddresses(
            evm=_evm_from_priv_hex(env_key),
            solana="<unavailable: BLOCKRUN_WALLET_KEY only derives EVM>",
            source="env",
        )

    mnemonic = _read_mnemonic_file()
    if mnemonic:
        return _derive_from_mnemonic(mnemonic)

    raise FileNotFoundError(
        f"No wallet found. Expected mnemonic at {_mnemonic_file()} or "
        f"{ENV_WALLET_KEY} env var.\n"
        f"Run: npx @blockrun/clawrouter setup"
    )


def _hex_balance_to_decimal(hex_str: str, decimals: int) -> float:
    raw = int(hex_str, 16) if hex_str else 0
    return raw / (10 ** decimals)


def fetch_usdc_base(evm_address: str, *, timeout: float = 6.0) -> Optional[float]:
    """Return USDC balance on Base for *evm_address*, or None on RPC failure."""
    addr_hex = evm_address.lower().removeprefix("0x").rjust(40, "0")
    data = "0x70a08231" + ("0" * 24) + addr_hex
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "eth_call",
        "params": [
            {"to": USDC_BASE_CONTRACT, "data": data},
            "latest",
        ],
    }
    try:
        resp = httpx.post(BASE_RPC, json=payload, timeout=timeout)
        resp.raise_for_status()
        result = resp.json().get("result")
        if not isinstance(result, str):
            return None
        return _hex_balance_to_decimal(result, USDC_BASE_DECIMALS)
    except (httpx.HTTPError, ValueError) as exc:
        logger.debug("fetch_usdc_base failed: %s", exc)
        return None


def fetch_usdc_solana(sol_address: str, *, timeout: float = 6.0) -> Optional[float]:
    """Return USDC balance on Solana for *sol_address*, or None on RPC failure."""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getTokenAccountsByOwner",
        "params": [
            sol_address,
            {"mint": USDC_SOLANA_MINT},
            {"encoding": "jsonParsed"},
        ],
    }
    try:
        resp = httpx.post(SOLANA_RPC, json=payload, timeout=timeout)
        resp.raise_for_status()
        accounts = (resp.json().get("result") or {}).get("value") or []
        total = 0.0
        for entry in accounts:
            info = entry.get("account", {}).get("data", {}).get("parsed", {}).get("info", {})
            amount = info.get("tokenAmount", {}).get("uiAmount")
            if isinstance(amount, (int, float)):
                total += float(amount)
        return total
    except (httpx.HTTPError, ValueError) as exc:
        logger.debug("fetch_usdc_solana failed: %s", exc)
        return None


def wallet_summary() -> dict:
    """Build a JSON-serializable summary used by slash + CLI commands."""
    try:
        addrs = load_addresses()
    except FileNotFoundError as exc:
        return {"ok": False, "error": str(exc)}

    base_balance = fetch_usdc_base(addrs.evm) if addrs.evm.startswith("0x") else None
    sol_balance = (
        fetch_usdc_solana(addrs.solana)
        if not addrs.solana.startswith("<")
        else None
    )

    return {
        "ok": True,
        "source": addrs.source,
        "evm": {
            "address": addrs.evm,
            "usdc_balance": base_balance,
            "chain": "base",
        },
        "solana": {
            "address": addrs.solana,
            "usdc_balance": sol_balance,
            "chain": "solana",
        },
        "mnemonic_path": str(_mnemonic_file()),
    }


CHAIN_FILE = _wallet_dir() / "payment-chain"

VALID_CHAINS = {"base", "solana"}


def current_payment_chain() -> str:
    """Return the active payment chain ('base' or 'solana')."""
    try:
        return CHAIN_FILE.read_text(encoding="utf-8").strip().lower() or "base"
    except OSError:
        return "base"


def set_payment_chain(chain: str) -> str:
    """Persist a new payment chain, return the confirmed value.

    Raises ``ValueError`` for unknown chain names.
    """
    chain = chain.strip().lower()
    if chain not in VALID_CHAINS:
        raise ValueError(
            f"Unknown chain '{chain}'. Valid: {', '.join(sorted(VALID_CHAINS))}"
        )
    CHAIN_FILE.parent.mkdir(parents=True, exist_ok=True)
    CHAIN_FILE.write_text(chain, encoding="utf-8")
    return chain


def format_summary(summary: dict) -> str:
    """Pretty-print ``wallet_summary()`` output for terminals and chat."""
    if not summary.get("ok"):
        return f"❌ {summary.get('error', 'wallet unavailable')}"

    def _fmt(balance: Optional[float]) -> str:
        if balance is None:
            return "—"
        return f"{balance:,.4f} USDC"

    evm = summary["evm"]
    sol = summary["solana"]
    active = current_payment_chain()

    return (
        "💰 *ClawRouter Wallet*\n\n"
        f"*Base*\n"
        f"  `{evm['address']}`\n"
        f"  {_fmt(evm['usdc_balance'])}\n"
        f"  [View on BaseScan](https://basescan.org/address/{evm['address']})\n\n"
        f"*Solana*\n"
        f"  `{sol['address']}`\n"
        f"  {_fmt(sol['usdc_balance'])}\n"
        f"  [View on Solscan](https://solscan.io/account/{sol['address']})\n\n"
        f"Paying on *{active.capitalize()}* · switch with "
        f"`/clawrouter wallet base|solana` (affects all ClawRouter clients).\n"
        f"_Shared with OpenClaw if installed. Back up your mnemonic — it "
        f"controls your funds: {summary['mnemonic_path']}_"
    )
