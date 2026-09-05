"""ClawRouter Hermes plugin — entry point.

Hermes' PluginManager discovers this module via the ``hermes_agent.plugins``
entry-point group and calls :func:`register` once at startup. We register:

- Tools (image / video / web_search) forwarded to the local ClawRouter proxy
- A single slash command ``/clawrouter`` with several subcommands
- A CLI subcommand ``hermes clawrouter <setup|wallet|doctor|route|stats>``
- A read-only skill ``clawrouter:guide``

The model-provider half (``ProviderProfile`` registration) is NOT done here
because Hermes loads model-provider plugins from
``~/.hermes/plugins/model-providers/<name>/`` only, not from entry-point
plugins. ``hermes clawrouter setup`` materializes that directory from the
bundled ``provider_template/`` resources.
"""

from __future__ import annotations

import logging
from pathlib import Path

from . import cli as _cli
from . import commands, proxy_supervisor, schemas, tools
from . import models as _models

__all__ = ["register"]

logger = logging.getLogger(__name__)

_VERSION = "0.4.0"


def register(ctx) -> None:
    """Wire all surfaces into the Hermes plugin context."""
    _install_compat()
    _register_tools(ctx)
    _register_hooks(ctx)
    _register_slash_command(ctx)
    _register_cli(ctx)
    _register_skill(ctx)
    # Best-effort, non-blocking probe so users see whether the proxy is up
    # without paying spawn latency at startup.
    try:
        status = proxy_supervisor.ensure_running(autospawn=False)
        if status.reachable:
            logger.info("clawrouter: proxy reachable at %s", status.base_url)
        else:
            logger.debug("clawrouter: proxy not yet running (will spawn on first use)")
    except Exception as exc:
        logger.debug("clawrouter: startup probe failed: %s", exc)


def _install_compat() -> None:
    """Best-effort setup for Hermes versions that need provider/config hints."""
    global _labels_patch_applied
    try:
        _cli.install_hermes_compat()
        _cli.patch_hermes_model_catalog()
        _labels_patch_applied = _patch_telegram_model_labels()
    except Exception as exc:
        logger.debug("clawrouter: compatibility setup skipped: %s", exc)


_labels_patch_applied = False


def _apply_telegram_label_patch_once(**_: Any) -> None:
    """pre_llm_call hook: patch Telegram adapters that load after register().

    Hermes ≥ 0.18 loads platform adapters lazily (as ``hermes_plugins.telegram.adapter``),
    typically after plugin registration — so the register-time attempt misses
    them and we retry here until an adapter shows up.
    """
    global _labels_patch_applied
    if _labels_patch_applied:
        return
    try:
        _labels_patch_applied = _patch_telegram_model_labels()
    except Exception as exc:
        logger.debug("clawrouter: deferred Telegram label patch failed: %s", exc)


def _patch_telegram_model_labels() -> bool:
    """Mark free ClawRouter models in Telegram picker labels only.

    We *wrap* the adapter's existing ``_build_model_keyboard`` rather than
    reimplementing it: the original owns pagination, layout, nav buttons, and
    the callback-data scheme, and we only relabel the model-selection buttons.
    This keeps the patch resilient if the adapter's keyboard internals change —
    if the method (or its ``mm:`` callback convention) ever goes away, the
    wrapper degrades to a transparent pass-through instead of breaking the
    picker.

    We never import the adapter module ourselves: since Hermes v0.18 it lives
    in a lazily-loaded platform plugin (``hermes_plugins.telegram.adapter``),
    and importing it here would both create a second, unused copy of the module
    (the running gateway never sees the patch) and re-add the startup cost the
    lazy loader exists to avoid. Instead we patch whatever adapter module is
    already in ``sys.modules``; :func:`_apply_telegram_label_patch_once` retries
    for adapters that load later. Returns True once an adapter is patched.
    """
    import sys as _sys

    patched = False
    for module_name, telegram in list(_sys.modules.items()):
        if telegram is None:
            continue
        if not (
            module_name == "gateway.platforms.telegram"  # Hermes ≤ 0.17
            or module_name.endswith(".telegram.adapter")  # ≥ 0.18 lazy platform plugin
        ):
            continue

        adapter = getattr(telegram, "TelegramAdapter", None)
        if adapter is None:
            continue
        if getattr(adapter, "_clawrouter_labels_patched", False):
            patched = True
            continue

        original = getattr(adapter, "_build_model_keyboard", None)
        if original is None:
            continue

        def _build_model_keyboard(
            self,
            model_list: list,
            page: int,
            *,
            _original=original,
            _module=telegram,
        ):
            markup, page_info = _original(self, model_list, page)
            try:
                # Resolve the button classes at call time: until the telegram
                # SDK is lazy-installed, the adapter publishes typing.Any
                # placeholders (not None) for these names and rebinds the real
                # classes afterwards. Anything non-instantiable → pass the
                # original keyboard through unchanged.
                inline_button = getattr(_module, "InlineKeyboardButton", None)
                inline_markup = getattr(_module, "InlineKeyboardMarkup", None)
                if not (
                    isinstance(inline_button, type)
                    and isinstance(inline_markup, type)
                    and getattr(inline_button, "__module__", "") != "typing"
                    and getattr(inline_markup, "__module__", "") != "typing"
                ):
                    return markup, page_info

                # Model-selection buttons carry ``mm:<abs_idx>`` callback data,
                # where abs_idx indexes into model_list. Rebuild only those
                # buttons with a free-aware label; pass every other button
                # (nav/back/cancel) through untouched. We rebuild instead of
                # mutating .text because telegram button objects may be frozen.
                new_rows = []
                for row in getattr(markup, "inline_keyboard", []) or []:
                    new_row = []
                    for btn in row:
                        cd = getattr(btn, "callback_data", "") or ""
                        if cd.startswith("mm:"):
                            try:
                                abs_idx = int(cd.split(":", 1)[1])
                                label = _models.picker_label(str(model_list[abs_idx]))
                                new_row.append(inline_button(label, callback_data=cd))
                                continue
                            except (ValueError, IndexError):
                                pass
                        new_row.append(btn)
                    new_rows.append(new_row)
                return inline_markup(new_rows), page_info
            except Exception:
                return markup, page_info

        adapter._build_model_keyboard = _build_model_keyboard
        adapter._clawrouter_labels_patched = True
        patched = True

    if not patched:
        logger.debug("clawrouter: no Telegram adapter loaded yet for free-model label patch")
    return patched


def _register_tools(ctx) -> None:
    ctx.register_tool(
        name="clawrouter_image_generate",
        toolset="clawrouter",
        schema=schemas.IMAGE_GENERATE,
        handler=tools.image_generate,
        description="Generate images via ClawRouter (x402-billed)",
        emoji="🎨",
    )
    ctx.register_tool(
        name="clawrouter_video_generate",
        toolset="clawrouter",
        schema=schemas.VIDEO_GENERATE,
        handler=tools.video_generate,
        description="Generate short videos via ClawRouter (x402-billed)",
        emoji="🎬",
    )
    ctx.register_tool(
        name="clawrouter_web_search",
        toolset="clawrouter",
        schema=schemas.WEB_SEARCH,
        handler=tools.web_search,
        description="Web search via ClawRouter Exa (x402-billed)",
        emoji="🔎",
    )


def _register_hooks(ctx) -> None:
    ctx.register_hook("pre_llm_call", _ensure_proxy_for_chat)
    # Hermes ≥ 0.18 loads the Telegram platform adapter lazily, after plugin
    # registration — retry the picker label patch once chat traffic starts.
    ctx.register_hook("pre_llm_call", _apply_telegram_label_patch_once)


def _ensure_proxy_for_chat(**kwargs) -> None:
    """Start the local proxy before Hermes calls the ClawRouter provider."""
    provider = str(
        kwargs.get("provider")
        or kwargs.get("provider_id")
        or kwargs.get("runtime_provider")
        or ""
    ).lower()
    base_url = str(kwargs.get("base_url") or kwargs.get("api_base") or "").lower()
    model = str(kwargs.get("model") or "").lower()

    if not (
        provider in {"clawrouter", "blockrun", "claw"}
        or "127.0.0.1:8402" in base_url
        or model.startswith("blockrun/")
    ):
        return

    status = proxy_supervisor.ensure_running()
    if not status.reachable:
        logger.warning("clawrouter: proxy unavailable before LLM call: %s", status.error)


def _register_slash_command(ctx) -> None:
    ctx.register_command(
        name="clawrouter",
        handler=commands.clawrouter_dispatch,
        description="ClawRouter wallet / stats / routing controls",
        args_hint="<wallet|stats|status|route|help>",
    )


def _register_cli(ctx) -> None:
    ctx.register_cli_command(
        name="clawrouter",
        help="ClawRouter setup, wallet, doctor, routing",
        setup_fn=_cli.register_cli,
        handler_fn=_cli.clawrouter_command,
        description=(
            "Manage the ClawRouter for Hermes plugin — install the model-provider "
            "plugin, inspect the wallet, diagnose health, and set the routing profile."
        ),
    )


def _register_skill(ctx) -> None:
    skill_path = Path(__file__).parent / "skills" / "clawrouter" / "SKILL.md"
    if not skill_path.exists():
        logger.debug("clawrouter: skill file missing at %s", skill_path)
        return
    try:
        ctx.register_skill(
            name="guide",
            path=skill_path,
            description="ClawRouter usage guide — models, pricing, wallet, slash commands",
        )
    except Exception as exc:
        logger.debug("clawrouter: skill registration failed: %s", exc)
