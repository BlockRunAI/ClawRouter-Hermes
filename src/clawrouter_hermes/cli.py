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

from . import models, proxy_supervisor, state, tools, wallet


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


def _env_file() -> Path:
    return _hermes_home() / ".env"


def _config_file() -> Path:
    return _hermes_home() / "config.yaml"


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
    setup_p.add_argument(
        "--set-default", action="store_true",
        help=(
            "Force ClawRouter to be the default provider/model in "
            "~/.hermes/config.yaml, overwriting any existing setting. "
            "By default setup leaves an existing default model alone."
        ),
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
        "Usage: hermes-clawrouter <setup|wallet|doctor|route|stats>\n\n"
        "Run `hermes-clawrouter <sub> --help` for details.",
    )


def _setup(args: argparse.Namespace) -> None:
    print("== ClawRouter for Hermes — setup ==")

    if _provider_plugin_dir().exists() and not args.force:
        print(f"✓ Model-provider plugin already at {_provider_plugin_dir()}")
        print("  Re-run with --force to overwrite.")
    else:
        _materialize_provider_plugin(force=args.force)
        print(f"✓ Wrote model-provider plugin to {_provider_plugin_dir()}")

    _ensure_local_api_key()
    print(f"✓ Ensured CLAWROUTER_API_KEY in {_env_file()}")

    config_changed = _configure_hermes_provider(
        set_default_force=bool(getattr(args, "set_default", False)),
    )
    if config_changed:
        print(f"✓ Registered ClawRouter in {_config_file()} for /model picker support")
    else:
        print(f"✓ ClawRouter already registered in {_config_file()}")

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

    print()
    print("Next: restart any running Hermes gateway, then choose ClawRouter in /model or run:")
    print("  hermes --provider clawrouter -m blockrun/auto")


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


def _ensure_local_api_key() -> None:
    """Seed a harmless local bearer so Hermes treats ClawRouter as configured."""
    os.environ.setdefault("CLAWROUTER_API_KEY", "clawrouter-local")
    path = _env_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    if "CLAWROUTER_API_KEY=" in existing:
        return
    prefix = existing.rstrip()
    suffix = "\n" if prefix else ""
    path.write_text(f"{prefix}{suffix}CLAWROUTER_API_KEY=clawrouter-local\n", encoding="utf-8")


def _configure_hermes_provider(*, set_default_force: bool = False) -> bool:
    """Add ClawRouter to Hermes config so gateway /model can list it."""
    try:
        import yaml  # type: ignore
    except Exception:
        return False

    path = _config_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = path.read_text(encoding="utf-8") if path.exists() else ""
    config = yaml.safe_load(raw) if raw.strip() else {}
    if not isinstance(config, dict):
        config = {}

    changed = False
    desired_model_defaults = {
        "default": "blockrun/auto",
        "provider": "clawrouter",
        "base_url": _base_url(),
    }
    model_cfg = config.setdefault("model", {})
    if isinstance(model_cfg, dict):
        if set_default_force:
            # Opt-in: overwrite all three keys.
            for key, value in desired_model_defaults.items():
                if model_cfg.get(key) != value:
                    model_cfg[key] = value
                    changed = True
        else:
            # Conservative: only seed when none of the three keys are set.
            # If any of {default, provider, base_url} exists, the user has
            # an existing config we mustn't half-overwrite (e.g. setting
            # base_url while leaving provider=anthropic would break them).
            already_has_any = any(
                model_cfg.get(k) is not None for k in desired_model_defaults
            )
            if not already_has_any:
                for key, value in desired_model_defaults.items():
                    model_cfg[key] = value
                    changed = True

    providers = config.setdefault("providers", {})
    if not isinstance(providers, dict):
        providers = {}
        config["providers"] = providers
        changed = True

    desired = {
        "name": "ClawRouter",
        "base_url": _base_url(),
        "key_env": "CLAWROUTER_API_KEY",
        "transport": "openai_chat",
        "default_model": "blockrun/auto",
        "discover_models": False,
        "models": models.chat_models(),
    }
    current = providers.get("clawrouter")
    if not isinstance(current, dict):
        providers["clawrouter"] = desired
        changed = True
    else:
        for key, value in desired.items():
            if current.get(key) != value:
                current[key] = value
                changed = True

    if changed or not path.exists():
        path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    return changed


def _base_url() -> str:
    return os.environ.get("CLAWROUTER_PROXY_URL", "http://127.0.0.1:8402/v1").rstrip("/")


def install_hermes_compat(*, force_provider: bool = False, set_default: bool = False) -> None:
    """Best-effort one-shot install for Hermes plugin/provider integration."""
    if force_provider or not _provider_plugin_dir().exists():
        _materialize_provider_plugin(force=force_provider)
    _ensure_local_api_key()
    _configure_hermes_provider(set_default_force=set_default)


def patch_hermes_model_catalog() -> None:
    """Expose ClawRouter models to Hermes' in-process /model picker."""
    try:
        from hermes_cli import models as hermes_models  # type: ignore
    except Exception:
        return
    provider_models = getattr(hermes_models, "_PROVIDER_MODELS", None)
    if isinstance(provider_models, dict):
        provider_models["clawrouter"] = models.chat_models()


def _wallet(args: argparse.Namespace) -> None:
    summary = wallet.wallet_summary()
    if args.json:
        print(json.dumps(summary, indent=2))
        return
    print(wallet.format_summary(summary))


def _check_provider_config() -> Tuple[bool, str]:
    """Doctor probe: is ``providers.clawrouter`` in ``~/.hermes/config.yaml``
    and does its URL match the proxy this process would use?

    Hermes' ``resolve_user_provider`` accepts ``api``, ``url``, or ``base_url``
    as the URL key (in that precedence order); we accept any of them so a
    hand-edited entry is still considered healthy.
    """
    path = _config_file()
    if not path.is_file():
        return False, f"{path} missing"
    try:
        import yaml  # type: ignore
    except Exception:
        return False, "PyYAML not importable"
    try:
        raw = path.read_text(encoding="utf-8")
        cfg = yaml.safe_load(raw) if raw.strip() else {}
    except Exception as exc:
        return False, f"{path}: {exc}"
    if not isinstance(cfg, dict):
        return False, f"{path}: top-level is not a mapping"
    entry = (cfg.get("providers") or {}).get("clawrouter")
    if not isinstance(entry, dict):
        return False, f"{path}: providers.clawrouter missing"
    url = entry.get("api") or entry.get("url") or entry.get("base_url") or ""
    if url.rstrip("/") != _base_url():
        return False, f"URL mismatch: config={url!r} expected={_base_url()!r}"
    return True, str(path)


def _check_api_key_present() -> Tuple[bool, str]:
    """Doctor probe: is ``CLAWROUTER_API_KEY`` resolvable by Hermes?

    Hermes' provider-detection requires the env var to exist before it
    will surface the provider. Either the live process env or the line
    in ``~/.hermes/.env`` is enough — Hermes loads both.
    """
    if os.environ.get("CLAWROUTER_API_KEY"):
        return True, "env"
    env_path = _env_file()
    if env_path.is_file():
        try:
            for line in env_path.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if stripped.startswith("#") or "=" not in stripped:
                    continue
                key, _, _ = stripped.partition("=")
                if key.strip() == "CLAWROUTER_API_KEY":
                    return True, str(env_path)
        except OSError:
            pass
    return False, f"not set; expected in env or {env_path}"


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

    cfg_ok, cfg_detail = _check_provider_config()
    rows.append(("providers.clawrouter in config.yaml", cfg_ok, cfg_detail))

    key_ok, key_detail = _check_api_key_present()
    rows.append(("CLAWROUTER_API_KEY available", key_ok, key_detail))

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


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="hermes-clawrouter")
    register_cli(parser)
    args = parser.parse_args(argv)
    clawrouter_command(args)
