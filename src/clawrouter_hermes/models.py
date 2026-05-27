"""Featured ClawRouter chat model catalog for Hermes pickers.

The full BlockRun catalog is maintained by the ClawRouter service. This list is
intentionally curated for Telegram/gateway pickers: it prevents Hermes from
rendering ``ClawRouter (0 models)`` without flooding small inline keyboards.
"""

from __future__ import annotations

CHAT_MODELS = (
    "blockrun/auto",
    "blockrun/free",
    "blockrun/eco",
    "blockrun/premium",
    "auto",
    "free",
    "eco",
    "premium",
    "openai/gpt-5.5",
    "openai/gpt-5.4",
    "openai/gpt-5-mini",
    "anthropic/claude-opus-4.7",
    "anthropic/claude-sonnet-4.6",
    "google/gemini-2.5-pro",
    "google/gemini-2.5-flash",
    "moonshot/kimi-k2.6",
    "deepseek/deepseek-chat",
    "zai/glm-5.1",
    "xai/grok-4-1-fast-reasoning",
    "xai/grok-code-fast-1",
    "minimax/minimax-m2.7",
    "nvidia/gpt-oss-120b",
)


def chat_models() -> list[str]:
    """Return a mutable copy of the curated chat model catalog."""
    return list(CHAT_MODELS)
