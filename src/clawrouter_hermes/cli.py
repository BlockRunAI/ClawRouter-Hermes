"""Argparse-based CLI subcommands for ``hermes clawrouter ...``.

Subcommands:
  - setup    materialize the model-provider plugin, verify Node + wallet
  - wallet   print wallet address + USDC balances
  - doctor   pass/fail health check
  - route    show/set routing profile
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from importlib import resources
from pathlib import Path
from typing import Iterable, List, Tuple

from . import proxy_supervisor, state, tools, wallet

_PROXY_BASE_URL = "http://127.0.0.1:8402/v1"
_PROVIDER_ENTRY = {
    "name": "ClawRouter",
    "api": _PROXY_BASE_URL,
    "transport": "openai_chat",
}


def _hermes_home() -> Path:
    """Mirror ``hermes_constants.get_hermes_home`` — honor ``HERMES_HOME``.

    We don't import from Hermes itself because this CLI also has to work
    before Hermes is on PYTHONPATH (during ``pip install`` testing).
    """
    val = os.environ.get("HERMES_HOME", "").strip()
    if val:
        return Path(val).expanduser()
    return Path.home() / ".hermes"


def _provider_plugin_dir() -> Path:
    return _hermes_home() / "plugins" / "model-providers" / "clawrouter"


def _hermes_config_path() -> Path:
    return _hermes_home() / "config.yaml"


def _ensure_provider_config() -> bool:
    """Write providers.clawrouter into ~/.hermes/config.yaml if absent or stale.

    Hermes has two separate provider systems: ProviderProfile (used by
    providers/__init__.py for building OpenAI clients) and ProviderDef (used
    by hermes_cli/providers.py resolve_provider_full for model selection and
    the --provider flag). The model-provider plugin materialized by setup only
    populates the first system. Without this entry in config.yaml the second
    system raises "Unknown provider 'clawrouter'" and falls back to auto.

    Returns True if the entry was written/updated, False if already present.
    """
    try:
        import yaml
    except ImportError:
        return False

    config_path = _hermes_config_path()
    config: dict = {}
    if config_path.is_file():
        try:
            config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        except Exception:
            config = {}

    providers = config.setdefault("providers", {})
    existing = providers.get("clawrouter") or {}
    if isinstance(existing, dict) and all(
        existing.get(k) == v for k, v in _PROVIDER_ENTRY.items()
    ):
        return False

    providers["clawrouter"] = dict(_PROVIDER_ENTRY)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        yaml.dump(config, default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )
    return True


def __getattr__(name: str):
    # Lazy attribute so tests can monkeypatch HOME / HERMES_HOME.
    if name == "HERMES_PLUGINS_DIR":
        return _provider_plugin_dir()
    raise AttributeError(name)


def register_cli(subparser: argparse.ArgumentParser) -> None:
    """Build the ``hermes clawrouter`` argument tree.

    Called by Hermes' plugin loader with a single ``ArgumentParser`` for our
    subcommand. We attach a ``func`` default on each leaf so dispatch goes
    through ``parser.set_defaults`` like the rest of Hermes.
    """
    subs = subparser.add_subparsers(dest="clawrouter_command", required=False)

    setup_p = subs.add_parser(
        "setup",
        help="Materialize the model-provider plugin and verify dependencies",
    )
    setup_p.add_argument(
        "--force", action="store_true",
        help="Overwrite an existing ~/.hermes/plugins/model-providers/clawrouter/",
    )
    setup_p.set_defaults(func=_setup)

    wallet_p = subs.add_parser("wallet", help="Show wallet address + USDC balances")
    wallet_p.add_argument("--json", action="store_true", help="Emit JSON instead of text")
    wallet_p.set_defaults(func=_wallet)

    doctor_p = subs.add_parser("doctor", help="Health check")
    doctor_p.set_defaults(func=_doctor)

    route_p = subs.add_parser("route", help="Show or set the routing profile")
    route_p.add_argument(
        "profile", nargs="?",
        choices=list(state.VALID_PROFILES),
        help="If omitted, prints the current profile.",
    )
    route_p.set_defaults(func=_route)

    stats_p = subs.add_parser("stats", help="Show proxy usage stats")
    stats_p.set_defaults(func=_stats)

    subparser.set_defaults(func=_default_help)


def clawrouter_command(args: argparse.Namespace) -> None:
    """Top-level dispatcher Hermes calls via ``handler_fn``."""
    fn = getattr(args, "func", None)
    if fn is None:
        _default_help(args)
        return
    fn(args)


# ---------------------------------------------------------------------------
# subcommands
# ---------------------------------------------------------------------------

def _default_help(_: argparse.Namespace) -> None:
    print(
        "Usage: hermes clawrouter <setup|wallet|doctor|route|stats>\n\n"
        "Run `hermes clawrouter <sub> --help` for details.",
    )


def _setup(args: argparse.Namespace) -> None:
    print("== ClawRouter for Hermes — setup ==")

    if _provider_plugin_dir().exists() and not args.force:
        print(f"✓ Model-provider plugin already at {_provider_plugin_dir()}")
        print("  Re-run with --force to overwrite.")
    else:
        _materialize_provider_plugin(force=args.force)
        print(f"✓ Wrote model-provider plugin to {_provider_plugin_dir()}")

    if shutil.which("npx") is None:
        print("✗ `npx` not found on PATH.")
        print("  Install Node.js 18+ from https://nodejs.org and re-run setup.")
    else:
        print("✓ Node / npx detected.")

    if wallet.MNEMONIC_FILE.is_file():
        try:
            addrs = wallet.load_addresses()
            print(f"✓ Wallet detected — EVM {addrs.evm}")
            print(f"               Solana {addrs.solana}")
            print("  Fund USDC on Base or Solana (≥$5 covers thousands of requests).")
        except Exception as exc:
            print(f"✗ Wallet file present but unreadable: {exc}")
    else:
        print("✗ No wallet found.")
        print(f"  Expected: {wallet.MNEMONIC_FILE}")
        print("  Run: npx @blockrun/clawrouter setup")

    if _ensure_provider_config():
        print(f"✓ Registered providers.clawrouter in {_hermes_config_path()}")
    else:
        print(f"✓ providers.clawrouter already in {_hermes_config_path()}")

    print()
    print("Next: open a Hermes chat with model `blockrun/auto` and ask anything.")


def _materialize_provider_plugin(*, force: bool) -> None:
    _provider_plugin_dir().parent.mkdir(parents=True, exist_ok=True)
    if _provider_plugin_dir().exists() and force:
        shutil.rmtree(_provider_plugin_dir())
    _provider_plugin_dir().mkdir(parents=True, exist_ok=True)

    template_dir = resources.files("clawrouter_hermes").joinpath("provider_template")
    # (template_filename, destination_filename) — template avoids __init__.py
    # so Python doesn't auto-import the file inside our own package context.
    file_map = (
        ("plugin.yaml", "plugin.yaml"),
        ("init.py.tmpl", "__init__.py"),
    )
    for src_name, dst_name in file_map:
        try:
            data = template_dir.joinpath(src_name).read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise RuntimeError(
                f"Provider template missing: {src_name} ({exc}). "
                "This indicates a broken package install."
            ) from exc
        (_provider_plugin_dir() / dst_name).write_text(data, encoding="utf-8")


def _wallet(args: argparse.Namespace) -> None:
    summary = wallet.wallet_summary()
    if args.json:
        print(json.dumps(summary, indent=2))
        return
    print(wallet.format_summary(summary))


def _doctor(_: argparse.Namespace) -> None:
    rows: List[Tuple[str, bool, str]] = []

    npx_ok = shutil.which("npx") is not None
    rows.append(("Node / npx on PATH", npx_ok, shutil.which("npx") or "—"))

    if npx_ok:
        try:
            ver = subprocess.run(
                ["node", "--version"], capture_output=True, text=True, timeout=5,
            )
            v = ver.stdout.strip() or "(unknown)"
            major_str = v.lstrip("v").split(".", 1)[0]
            ok = major_str.isdigit() and int(major_str) >= 18
            rows.append(("Node >= 18", ok, v))
        except (OSError, subprocess.SubprocessError) as exc:
            rows.append(("Node >= 18", False, str(exc)))

    rows.append(
        ("Wallet mnemonic present",
         wallet.MNEMONIC_FILE.is_file(),
         str(wallet.MNEMONIC_FILE)),
    )

    if wallet.MNEMONIC_FILE.is_file():
        mode = wallet.MNEMONIC_FILE.stat().st_mode & 0o777
        rows.append(("Mnemonic mode 0o600", mode == 0o600, f"0o{mode:o}"))

    rows.append(
        ("Model-provider plugin installed",
         _provider_plugin_dir().is_dir(),
         str(_provider_plugin_dir())),
    )

    try:
        import yaml
        config_path = _hermes_config_path()
        cfg = yaml.safe_load(config_path.read_text(encoding="utf-8")) if config_path.is_file() else {}
        existing = (cfg or {}).get("providers", {}).get("clawrouter") or {}
        cfg_ok = isinstance(existing, dict) and all(
            existing.get(k) == v for k, v in _PROVIDER_ENTRY.items()
        )
    except Exception:
        cfg_ok = False
    rows.append(
        ("providers.clawrouter in config.yaml", cfg_ok, str(_hermes_config_path())),
    )

    proxy_status = proxy_supervisor.status()
    rows.append(
        ("Proxy reachable",
         proxy_status.reachable,
         proxy_status.base_url),
    )

    if wallet.MNEMONIC_FILE.is_file():
        summary = wallet.wallet_summary()
        if summary.get("ok"):
            base_bal = summary["evm"].get("usdc_balance")
            sol_bal = summary["solana"].get("usdc_balance")
            has_funds = any(
                isinstance(b, (int, float)) and b > 0 for b in (base_bal, sol_bal)
            )
            rows.append(
                ("USDC balance > 0 on Base or Solana",
                 has_funds,
                 f"base={base_bal} solana={sol_bal}"),
            )

    name_w = max(len(r[0]) for r in rows) + 2
    failures = 0
    for label, ok, detail in rows:
        mark = "✓" if ok else "✗"
        if not ok:
            failures += 1
        print(f"  {mark}  {label.ljust(name_w)} {detail}")

    print()
    if failures == 0:
        print("All checks passed.")
    else:
        print(f"{failures} check(s) failed — see above.")
        sys.exit(1)


def _route(args: argparse.Namespace) -> None:
    if args.profile is None:
        print(f"Current routing profile: {state.get_profile()}")
        print(f"Valid profiles: {', '.join(state.VALID_PROFILES)}")
        return
    new_profile = state.set_profile(args.profile)
    print(f"✓ Routing profile set to '{new_profile}'.")


def _stats(_: argparse.Namespace) -> None:
    print(json.dumps(tools.proxy_stats(), indent=2))
