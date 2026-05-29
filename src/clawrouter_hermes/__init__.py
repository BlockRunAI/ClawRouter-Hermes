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

_VERSION = "0.1.0"


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
    try:
        _cli.install_hermes_compat()
        _cli.patch_hermes_model_catalog()
        _patch_telegram_model_labels()
    except Exception as exc:
        logger.debug("clawrouter: compatibility setup skipped: %s", exc)


def _patch_telegram_model_labels() -> None:
    """Mark free ClawRouter models in Telegram picker labels only.

    We *wrap* the adapter's existing ``_build_model_keyboard`` rather than
    reimplementing it: the original owns pagination, layout, nav buttons, and
    the callback-data scheme, and we only relabel the model-selection buttons.
    This keeps the patch resilient if the adapter's keyboard internals change —
    if the method (or its ``mm:`` callback convention) ever goes away, the
    wrapper degrades to a transparent pass-through instead of breaking the
    picker.
    """
    try:
        from gateway.platforms import telegram
    except Exception:
        return

    adapter = getattr(telegram, "TelegramAdapter", None)
    if adapter is None or getattr(adapter, "_clawrouter_labels_patched", False):
        return

    original = getattr(adapter, "_build_model_keyboard", None)
    inline_button = getattr(telegram, "InlineKeyboardButton", None)
    inline_markup = getattr(telegram, "InlineKeyboardMarkup", None)
    if original is None or inline_button is None or inline_markup is None:
        return

    def _build_model_keyboard(self, model_list: list, page: int):
        markup, page_info = original(self, model_list, page)

        # Model-selection buttons carry ``mm:<abs_idx>`` callback data, where
        # abs_idx indexes into model_list. Rebuild only those buttons with a
        # free-aware label; pass every other button (nav/back/cancel) through
        # untouched. We rebuild instead of mutating .text because telegram
        # button objects may be frozen.
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

    adapter._build_model_keyboard = _build_model_keyboard
    adapter._clawrouter_labels_patched = True


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
