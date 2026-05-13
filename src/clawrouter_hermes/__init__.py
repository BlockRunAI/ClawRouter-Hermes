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

__all__ = ["register"]

logger = logging.getLogger(__name__)

_VERSION = "0.1.0"


def register(ctx) -> None:
    """Wire all surfaces into the Hermes plugin context."""
    _register_tools(ctx)
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
